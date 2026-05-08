"""
module2_ifc_read.py
--------------------
IFC model reader for BIMGuard compliance checking.

Extraction depth (all four gaps addressed):

  1. Rich property values
       - Data type (IfcReal, IfcInteger, IfcLabel, …)
       - Unit of measure from the property definition
       - Nominal / lower / upper bounds from IfcPropertyBoundedValue
       - Enumeration lists from IfcPropertyEnumeratedValue

  2. Relationships
       - Spatial containment (storey, space)
       - Element type object (IfcDoorType, IfcWallType, …) + its properties
       - Parent/child decomposition (aggregates)

  3. Material / composition
       - IfcMaterial (single material name)
       - IfcMaterialLayerSet / LayerSetUsage (layers with thickness)
       - IfcMaterialConstituentSet (named constituents)

  4. Direct attributes vs. properties
       - Pset properties searched first (nominated set → all sets → Qto sets)
       - Direct IFC attributes (e.g. OverallHeight, OverallWidth) as final fallback
       - element.get_info() exposes every schema-defined attribute

The public interface of extract_for_compliance() is unchanged so Module 4
continues to work — it now additionally receives richer per-element metadata.
"""

import json
from pathlib import Path

try:
    import ifcopenshell
    import ifcopenshell.util.element

    _IFCOPENSHELL_AVAILABLE = True
except ImportError:
    _IFCOPENSHELL_AVAILABLE = False

try:
    from .ifc_quality.validator import IFCValidator
    from .ifc_quality.improver import improve_ifc_file
    _QUALITY_TOOLS_AVAILABLE = True
except ImportError:
    _QUALITY_TOOLS_AVAILABLE = False

# Minimum quality score (0-100) required before extraction proceeds.
# Files below this threshold are auto-improved before loading.
IFC_MIN_QUALITY_SCORE = 70


# ── IFC property-type → Python type label ────────────────────────────────────
_IFC_TYPE_MAP = {
    "IfcReal":             "real",
    "IfcInteger":          "integer",
    "IfcBoolean":          "boolean",
    "IfcLogical":          "boolean",
    "IfcLabel":            "string",
    "IfcText":             "string",
    "IfcIdentifier":       "string",
    "IfcPositiveLengthMeasure": "real",
    "IfcLengthMeasure":    "real",
    "IfcAreaMeasure":      "real",
    "IfcVolumeMeasure":    "real",
    "IfcPlaneAngleMeasure":"real",
    "IfcCountMeasure":     "integer",
    "IfcMassMeasure":      "real",
    "IfcTimeMeasure":      "real",
    "IfcThermalTransmittanceMeasure": "real",
}


class Module2_IFCRead:
    """Full IFC reader for Module 2 compliance extraction."""

    def __init__(self, file_path: Path | str | None = None):
        self.file_path       = Path(file_path) if file_path else None
        self.ifc_file        = None
        self.quality_report: dict       = {}
        self.quality_warnings: list[str] = []
        if self.file_path:
            self.load_ifc_file()

    # ── Core load / schema helpers ────────────────────────────────────────────

    def load_ifc_file(self):
        if not _IFCOPENSHELL_AVAILABLE:
            raise ImportError("ifcopenshell is not installed.")
        if not self.file_path or not self.file_path.exists():
            raise FileNotFoundError(f"IFC file not found: {self.file_path}")

        load_path = self.file_path
        self.quality_report: dict = {}
        self.quality_warnings: list[str] = []

        if _QUALITY_TOOLS_AVAILABLE:
            results = IFCValidator(str(load_path)).validate()
            self.quality_report = results
            score = results.get("overall", {}).get("score", 100)

            if score < IFC_MIN_QUALITY_SCORE:
                improved_path = load_path.with_stem(load_path.stem + "_improved")
                print(f"IFC quality {score:.1f}% < {IFC_MIN_QUALITY_SCORE}% — "
                      f"auto-improving → {improved_path.name}")
                improve_ifc_file(str(load_path), str(improved_path))
                load_path = improved_path
                self.quality_warnings.append(
                    f"Quality {score:.1f}% was below threshold; "
                    f"auto-improved file used: {improved_path.name}"
                )
            elif score < 80:
                self.quality_warnings.append(
                    f"IFC quality is fair ({score:.1f}%). "
                    "Consider running the IFC improver for better results."
                )

        self.ifc_file = ifcopenshell.open(str(load_path))
        return self.ifc_file

    def get_all_elements(self, ifc_type: str = "IfcBuildingElement") -> list:
        if not self.ifc_file:
            raise ValueError("No IFC file loaded.")
        return self.ifc_file.by_type(ifc_type)

    def _resolve_building_elements(self) -> list:
        for ifc_type in ("IfcBuildingElement", "IfcBuiltElement", "IfcElement"):
            try:
                return self.ifc_file.by_type(ifc_type)
            except Exception:
                continue
        return []

    def extract_properties(self, element) -> dict:
        """Return simplified {pset_name: {prop: value}} dict (legacy method)."""
        return ifcopenshell.util.element.get_psets(element)

    # ── Gap 1: Rich property extraction ──────────────────────────────────────

    def extract_rich_properties(self, element) -> dict[str, dict]:
        """
        Return the full property tree for one element.

        Structure:
          {
            "<PsetName>": {
              "<PropName>": {
                "value":       scalar_value,
                "value_type":  "real" | "integer" | "string" | "boolean" | "enum" | "bounded",
                "unit":        "mm" | "m²" | … | None,
                "lower_bound": float | None,
                "upper_bound": float | None,
                "enum_values": [str, …] | None,
                "ifc_type":    "IfcPropertySingleValue" | …
              }
            }
          }
        """
        result: dict[str, dict] = {}
        for rel in getattr(element, "IsDefinedBy", []):
            if not rel.is_a("IfcRelDefinesByProperties"):
                continue
            pdef = rel.RelatingPropertyDefinition
            if pdef.is_a("IfcPropertySet"):
                pset_data = {}
                for prop in getattr(pdef, "HasProperties", []):
                    pset_data[prop.Name] = self._parse_ifc_property(prop)
                result[pdef.Name] = pset_data
            elif pdef.is_a("IfcElementQuantity"):
                # Qto_ quantity sets
                qset_data = {}
                for qty in getattr(pdef, "Quantities", []):
                    qset_data[qty.Name] = self._parse_ifc_quantity(qty)
                result[pdef.Name] = qset_data
        return result

    def _parse_ifc_property(self, prop) -> dict:
        """Decode one IFC property into a rich dict."""
        ifc_type = prop.is_a()

        if ifc_type == "IfcPropertySingleValue":
            nv = prop.NominalValue
            if nv is None:
                return {"value": None, "value_type": "null", "unit": None,
                        "ifc_type": ifc_type}
            raw        = getattr(nv, "wrappedValue", nv)
            vtype      = _IFC_TYPE_MAP.get(nv.is_a(), "string")
            unit_label = self._resolve_unit(getattr(prop, "Unit", None))
            return {
                "value":       raw,
                "value_type":  vtype,
                "unit":        unit_label,
                "lower_bound": None,
                "upper_bound": None,
                "enum_values": None,
                "ifc_type":    ifc_type,
            }

        if ifc_type == "IfcPropertyBoundedValue":
            lo = getattr(prop.LowerBoundValue, "wrappedValue", None) \
                 if prop.LowerBoundValue else None
            hi = getattr(prop.UpperBoundValue, "wrappedValue", None) \
                 if prop.UpperBoundValue else None
            sp = getattr(prop.SetPointValue, "wrappedValue", None) \
                 if getattr(prop, "SetPointValue", None) else None
            return {
                "value":       sp if sp is not None else lo,
                "value_type":  "bounded",
                "unit":        self._resolve_unit(getattr(prop, "Unit", None)),
                "lower_bound": lo,
                "upper_bound": hi,
                "enum_values": None,
                "ifc_type":    ifc_type,
            }

        if ifc_type == "IfcPropertyEnumeratedValue":
            values = [
                getattr(v, "wrappedValue", v)
                for v in (prop.EnumerationValues or [])
            ]
            return {
                "value":       values[0] if values else None,
                "value_type":  "enum",
                "unit":        None,
                "lower_bound": None,
                "upper_bound": None,
                "enum_values": values,
                "ifc_type":    ifc_type,
            }

        # IfcPropertyListValue, IfcPropertyTableValue, etc.
        return {"value": str(prop), "value_type": "complex",
                "unit": None, "ifc_type": ifc_type}

    def _parse_ifc_quantity(self, qty) -> dict:
        """Decode one IFC quantity (area, length, count, …)."""
        for attr in ("LengthValue", "AreaValue", "VolumeValue",
                     "WeightValue", "CountValue", "TimeValue"):
            v = getattr(qty, attr, None)
            if v is not None:
                return {"value": v, "value_type": "real",
                        "unit": attr.replace("Value", "").lower(),
                        "ifc_type": qty.is_a()}
        return {"value": None, "value_type": "unknown", "ifc_type": qty.is_a()}

    def _resolve_unit(self, unit_ref) -> str | None:
        """Convert an IfcUnit reference to a human-readable label."""
        if unit_ref is None:
            return None
        try:
            ifc_t = unit_ref.is_a()
            if ifc_t == "IfcSIUnit":
                prefix = getattr(unit_ref, "Prefix", None) or ""
                name   = getattr(unit_ref, "Name",   "") or ""
                _SI_ABBREV = {
                    "METRE": "m", "SQUARE_METRE": "m²", "CUBIC_METRE": "m³",
                    "GRAM": "g", "SECOND": "s", "AMPERE": "A",
                    "KELVIN": "K", "RADIAN": "rad", "STERADIAN": "sr",
                    "HERTZ": "Hz", "NEWTON": "N", "PASCAL": "Pa",
                }
                _PREFIX = {
                    "MILLI": "m", "CENTI": "c", "KILO": "k", "MEGA": "M",
                }
                abbrev = _SI_ABBREV.get(name, name.lower())
                return f"{_PREFIX.get(prefix,'')}{abbrev}" if abbrev else None
            if ifc_t == "IfcConversionBasedUnit":
                return getattr(unit_ref, "Name", None)
            if ifc_t == "IfcContextDependentUnit":
                return getattr(unit_ref, "Name", None)
        except Exception:
            pass
        return None

    # ── Gap 2: Relationships ──────────────────────────────────────────────────

    def get_spatial_location(self, element) -> dict:
        """
        Return the spatial context of an element.

        Returns:
            {storey_name, storey_elevation, space_name, building_name}
        """
        storey_name = storey_elev = space_name = building_name = None
        try:
            for rel in getattr(element, "ContainedInStructure", []):
                container = rel.RelatingStructure
                if container.is_a("IfcSpace"):
                    space_name = getattr(container, "LongName", None) \
                                 or getattr(container, "Name", None)
                if container.is_a("IfcBuildingStorey"):
                    storey_name = getattr(container, "Name", None)
                    storey_elev = getattr(container, "Elevation", None)
                if container.is_a("IfcBuilding"):
                    building_name = getattr(container, "Name", None)
            # Walk up for storey if only space was found
            if space_name and storey_name is None:
                for rel in getattr(element, "ContainedInStructure", []):
                    cont = rel.RelatingStructure
                    for rel2 in getattr(cont, "Decomposes", []):
                        parent = rel2.RelatingObject
                        if parent.is_a("IfcBuildingStorey"):
                            storey_name = getattr(parent, "Name", None)
        except Exception:
            pass
        return {
            "storey_name":      storey_name,
            "storey_elevation": float(storey_elev) if storey_elev is not None else None,
            "space_name":       space_name,
            "building_name":    building_name,
        }

    def get_type_info(self, element) -> dict:
        """
        Return the element's type object and its properties.

        Returns:
            {type_name, type_guid, type_properties: {pset: {prop: value}}}
        """
        type_name = type_guid = None
        type_props: dict = {}
        try:
            el_type = ifcopenshell.util.element.get_type(element)
            if el_type:
                type_name  = getattr(el_type, "Name", None)
                type_guid  = getattr(el_type, "GlobalId", None)
                type_props = self.extract_rich_properties(el_type)
        except Exception:
            pass
        return {
            "type_name":       type_name,
            "type_guid":       type_guid,
            "type_properties": type_props,
        }

    def get_decomposition(self, element) -> dict:
        """
        Return immediate parent and children in the decomposition hierarchy.

        Returns:
            {parent_name, parent_type, children: [{name, type, guid}]}
        """
        parent_name = parent_type = None
        children: list[dict] = []
        try:
            for rel in getattr(element, "Decomposes", []):
                parent = rel.RelatingObject
                parent_name = getattr(parent, "Name", None)
                parent_type = parent.is_a()
            for rel in getattr(element, "IsDecomposedBy", []):
                for child in rel.RelatedObjects:
                    children.append({
                        "name": getattr(child, "Name", None),
                        "type": child.is_a(),
                        "guid": child.GlobalId,
                    })
        except Exception:
            pass
        return {
            "parent_name": parent_name,
            "parent_type": parent_type,
            "children":    children,
        }

    # ── Gap 3: Material / composition ─────────────────────────────────────────

    def get_material_info(self, element) -> dict:
        """
        Return material data for an element.

        Returns:
            {
              material_type: "single" | "layer_set" | "constituent_set" | "profile_set" | "none",
              layers: [{name, thickness_mm, category}],
              materials: [str],  # flat material name list
            }
        """
        layers: list[dict] = []
        material_names: list[str] = []
        mat_type = "none"

        try:
            mat = ifcopenshell.util.element.get_material(element)
            if mat is None:
                return {"material_type": "none", "layers": [], "materials": []}

            t = mat.is_a()

            if t == "IfcMaterial":
                mat_type = "single"
                material_names = [mat.Name or ""]

            elif t in ("IfcMaterialLayerSet", "IfcMaterialLayerSetUsage"):
                mat_type = "layer_set"
                layer_set = mat.ForLayerSet if t == "IfcMaterialLayerSetUsage" else mat
                for layer in getattr(layer_set, "MaterialLayers", []):
                    name = getattr(layer.Material, "Name", "Unknown") \
                           if layer.Material else "Unknown"
                    thickness = getattr(layer, "LayerThickness", None)
                    category  = getattr(layer, "Category", None)
                    layers.append({
                        "name":         name,
                        "thickness_mm": float(thickness) if thickness is not None else None,
                        "category":     category,
                    })
                    material_names.append(name)

            elif t == "IfcMaterialConstituentSet":
                mat_type = "constituent_set"
                for constituent in getattr(mat, "MaterialConstituents", []):
                    name = getattr(constituent.Material, "Name", "Unknown") \
                           if constituent.Material else "Unknown"
                    fraction = getattr(constituent, "Fraction", None)
                    layers.append({
                        "name":      name,
                        "fraction":  float(fraction) if fraction is not None else None,
                        "category":  getattr(constituent, "Category", None),
                    })
                    material_names.append(name)

            elif t == "IfcMaterialProfileSet":
                mat_type = "profile_set"
                for profile in getattr(mat, "MaterialProfiles", []):
                    name = getattr(profile.Material, "Name", "Unknown") \
                           if profile.Material else "Unknown"
                    material_names.append(name)

        except Exception:
            pass

        return {
            "material_type": mat_type,
            "layers":        layers,
            "materials":     material_names,
        }

    # ── Gap 4: Direct IFC attributes ──────────────────────────────────────────

    def get_direct_attributes(self, element) -> dict:
        """
        Return all schema-defined direct attributes of an element.

        Unlike Pset properties these are encoded directly in the IFC entity:
        e.g. IfcDoor.OverallHeight, IfcWindow.OverallWidth, IfcSlab.PredefinedType

        Excludes relationship handles (those are object references, not values).
        """
        try:
            info = element.get_info()
        except Exception:
            return {}

        _SKIP = {
            "id", "type", "GlobalId", "OwnerHistory",
            "ObjectPlacement", "Representation",
            "HasAssignments", "IsDecomposedBy", "Decomposes",
            "HasAssociations", "IsDefinedBy", "ReferencedBy",
            "ContainedInStructure", "ConnectedTo", "ConnectedFrom",
            "FillsVoids", "HasOpenings",
        }
        result = {}
        for k, v in info.items():
            if k in _SKIP:
                continue
            if v is None:
                continue
            # Keep only scalar values — skip IFC object references
            if isinstance(v, (str, int, float, bool)):
                result[k] = v
            elif isinstance(v, tuple):
                # Coordinate tuples (IfcCartesianPoint), enum values, etc.
                result[k] = list(v)
        return result

    # ── Compliance extraction (all fallbacks) ─────────────────────────────────

    def extract_for_compliance(self, rules: list[dict]) -> list[dict]:
        """
        For each rule, find matching IFC elements and extract the property value.

        Property search order per element:
          1. Nominated property set (property_set field in rule)
          2. All Psets and Qto_ quantity sets
          3. Direct IFC schema attributes (OverallHeight, OverallWidth, …)

        Element results now include rich metadata (type, unit, bounds, spatial
        location, materials) alongside the scalar actual_value used by Module 4.
        """
        if not self.ifc_file:
            raise ValueError("No IFC file loaded.")

        results = []
        for rule in rules:
            target    = str(rule.get("target_ifc_class") or "").strip()
            prop_name = str(rule.get("property_name")    or "").strip()
            prop_set  = str(rule.get("property_set")     or "").strip()
            operator  = str(rule.get("operator")         or "").strip()

            if not target or (not prop_name and operator not in ("exists", "not_exists")):
                continue

            try:
                elements = self.ifc_file.by_type(target)
            except Exception:
                elements = []

            element_results = []
            for el in elements:
                actual_value = None
                found_pset   = None
                rich_detail: dict = {}

                # ── Pass 1: simple get_psets (fast path) ──────────────────
                try:
                    psets_simple = ifcopenshell.util.element.get_psets(
                        el, psets_only=False
                    )
                except Exception:
                    psets_simple = {}

                if prop_set and prop_set in psets_simple:
                    v = psets_simple[prop_set].get(prop_name)
                    if v is not None:
                        actual_value = v
                        found_pset   = prop_set

                if actual_value is None and prop_name:
                    for ps_name, props in psets_simple.items():
                        if isinstance(props, dict) and prop_name in props:
                            v = props[prop_name]
                            if v is not None:
                                actual_value = v
                                found_pset   = ps_name
                                break

                # ── Pass 2: rich property extraction (for type/unit/bounds) ─
                if prop_name and found_pset:
                    try:
                        rich_all  = self.extract_rich_properties(el)
                        rich_pset = rich_all.get(found_pset, {})
                        rich_prop = rich_pset.get(prop_name, {})
                        if rich_prop:
                            rich_detail = rich_prop
                    except Exception:
                        pass

                # ── Pass 3: direct IFC attribute fallback ─────────────────
                if actual_value is None and prop_name:
                    try:
                        direct = self.get_direct_attributes(el)
                        v = direct.get(prop_name)
                        if v is not None:
                            actual_value = v
                            found_pset   = "direct_attribute"
                    except Exception:
                        pass

                # ── Spatial, type, material context ───────────────────────
                try:
                    spatial  = self.get_spatial_location(el)
                    type_inf = self.get_type_info(el)
                    mat_info = self.get_material_info(el)
                except Exception:
                    spatial = type_inf = mat_info = {}

                element_results.append({
                    # Core compliance fields (consumed by Module 4)
                    "guid":         el.GlobalId,
                    "name":         getattr(el, "Name", None) or f"{target}_{el.id()}",
                    "actual_value": actual_value,
                    "found_pset":   found_pset,
                    "found":        actual_value is not None,
                    # Gap 1: rich property metadata
                    "value_type":   rich_detail.get("value_type"),
                    "value_unit":   rich_detail.get("unit"),
                    "lower_bound":  rich_detail.get("lower_bound"),
                    "upper_bound":  rich_detail.get("upper_bound"),
                    "enum_values":  rich_detail.get("enum_values"),
                    # Gap 2: spatial + type
                    "storey":       spatial.get("storey_name"),
                    "space":        spatial.get("space_name"),
                    "element_type": type_inf.get("type_name"),
                    # Gap 3: material
                    "materials":    mat_info.get("materials", []),
                    "material_layers": mat_info.get("layers", []),
                })

            results.append({
                "rule_id":          rule.get("id"),
                "rule_ref":         str(rule.get("reference")   or ""),
                "rule_desc":        str(rule.get("description") or ""),
                "target_ifc_class": target,
                "property_name":    prop_name,
                "property_set":     prop_set,
                "operator":         operator,
                "check_value":      self._decode_json_val(rule.get("check_value")),
                "value_min":        self._decode_json_val(rule.get("value_min")),
                "value_max":        self._decode_json_val(rule.get("value_max")),
                "unit":             str(rule.get("unit")     or ""),
                "severity":         str(rule.get("severity") or "mandatory"),
                "elements":         element_results,
            })

        return results

    def get_full_element_data(self, element) -> dict:
        """
        Return everything about one IFC element — for inspection / debugging.

        Combines: direct attributes, rich properties, type, spatial, materials,
        decomposition.
        """
        return {
            "guid":             element.GlobalId,
            "ifc_type":         element.is_a(),
            "name":             getattr(element, "Name", None),
            "description":      getattr(element, "Description", None),
            "direct_attributes": self.get_direct_attributes(element),
            "properties":       self.extract_rich_properties(element),
            "spatial":          self.get_spatial_location(element),
            "type_info":        self.get_type_info(element),
            "materials":        self.get_material_info(element),
            "decomposition":    self.get_decomposition(element),
        }

    # ── Utility ───────────────────────────────────────────────────────────────

    def extract_geometry(self) -> list[dict]:
        """Return {id, type, properties} for all building elements (legacy)."""
        if not self.ifc_file:
            raise ValueError("No IFC file loaded.")
        return [
            {"id": el.id(), "type": el.is_a(),
             "properties": self.extract_properties(el)}
            for el in self._resolve_building_elements()
        ]

    def extract_summary_counts(
        self,
        include_openings: bool = True,
        include_spaces: bool = True,
        include_type_definitions: bool = False,
    ) -> dict:
        if not self.ifc_file:
            raise ValueError("No IFC file loaded.")
        built  = len(self._resolve_building_elements())
        phys   = self._count_by_type("IfcElement")
        prods  = self._count_by_type("IfcProduct")
        opens  = self._count_by_type("IfcOpeningElement")
        spaces = self._count_by_type("IfcSpace")
        types  = self._count_by_type("IfcElementType")
        adj_phys  = max(0, phys  - (opens  if not include_openings else 0))
        adj_prods = max(0, prods - (opens  if not include_openings else 0)
                                 - (spaces if not include_spaces    else 0)
                                 + (types  if include_type_definitions else 0))
        return {
            "built_elements": built,
            "all_physical_elements": phys,
            "all_products": prods,
            "adjusted_physical_elements": adj_phys,
            "adjusted_products": adj_prods,
            "filters": {
                "include_openings": include_openings,
                "include_spaces": include_spaces,
                "include_type_definitions": include_type_definitions,
            },
            "excluded_or_added": {
                "openings": opens, "spaces": spaces, "type_definitions": types,
            },
        }

    def _count_by_type(self, ifc_type: str) -> int:
        try:
            return len(self.ifc_file.by_type(ifc_type))
        except Exception:
            return 0

    @staticmethod
    def _decode_json_val(v):
        """Decode DB JSON-encoded check_value / value_min / value_max."""
        if v is None:
            return None
        if isinstance(v, (int, float)):
            return float(v)
        try:
            decoded = json.loads(str(v))
            return float(decoded) if decoded is not None else None
        except (json.JSONDecodeError, ValueError, TypeError):
            return None
