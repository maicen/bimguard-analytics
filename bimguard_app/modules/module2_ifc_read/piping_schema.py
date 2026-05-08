"""
app/modules/piping_schema.py

Data contract for piping compliance checking in BIM Guard.

This module defines the canonical structure of piping elements passed between
Module2 (IFC reader, owned by Sam) and Module4 (comparators, owned by the
piping compliance team). Every piping-related element exiting Module2 must
conform to PipingElement. Every piping comparator in Module4 consumes
list[PipingElement].

OWNERSHIP
    - PipingElement schema: defined here, evolved by PR to this file.
    - Module2 producer (Sam): extracts from IFC via ifcopenshell, normalises
      materials, classifies environment, emits list[PipingElement].
    - Module4 consumers (piping compliance team): galvanic, crevice,
      clearance, centre-to-centre, seismic reservation — each takes
      list[PipingElement] plus a RulePack and returns list[Issue].

UNITS — SI THROUGHOUT
    Length:       metres (m)                      — fields without suffix
    Diameter:     millimetres (mm)                — fields end _mm
    Temperature:  degrees Celsius (°C)            — fields end _c
    Mass:         kilograms (kg)                  — fields end _kg
    Pressure:     bar                             — fields end _bar
    Voltage:      volts (V)                       — fields end _v
    Area:         square metres (m²)              — fields end _m2

COORDINATES
    World coordinates from the IFC file, via ifcopenshell, with Z up and
    units converted to metres. If the IFC uses different length units,
    Module2 converts before populating this schema.

NULLABILITY POLICY
    Fields are Optional where the underlying IFC data is frequently missing.
    Comparators are expected to handle None gracefully. If a comparator
    cannot run because a required field is None, it emits a Low-severity
    issue with mechanism="data_quality" pointing at the offending element
    rather than crashing.

VERSIONING
    Bump SCHEMA_VERSION on any breaking change. Additive fields (new
    optional attributes) are not breaking. Renaming or removing fields,
    changing types, or tightening nullability all require a bump and a
    migration note in CHANGELOG.
"""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field, is_dataclass
from enum import Enum
from typing import Any, Literal, Optional

SCHEMA_VERSION = "1.0.0"


# ---------------------------------------------------------------------------
# Canonical material keys
# ---------------------------------------------------------------------------
# Module2 normalises any IFC material string to one of these keys. If a
# material cannot be identified confidently, use "Unknown" and add a note
# to extraction_warnings. The corrosion rule packs key off these strings,
# so they must match exactly (case-sensitive).

CANONICAL_MATERIALS: frozenset[str] = frozenset(
    {
        # Stainless steels
        "SS304",
        "SS304L",
        "SS316",
        "SS316L",
        "SS316Ti",
        "Duplex2205",
        "SuperDuplex2507",
        # Carbon and galvanised steels
        "CarbonSteel",
        "GalvanisedSteel",
        "BlackSteel",
        # Copper and copper alloys
        "Copper_C12200",
        "Brass_C46400",
        "CuNi_9010",
        "CuNi_7030",
        # Non-ferrous
        "Aluminium",
        "Titanium",
        # Plastics (relevant to crevice-at-support scenarios only)
        "PVC",
        "PEX",
        "HDPE",
        "PPR",
        # Cast
        "DuctileIron",
        "CastIron",
        # Sentinel
        "Unknown",
    }
)


# ---------------------------------------------------------------------------
# Environment classification
# ---------------------------------------------------------------------------
# Aligned with EN ISO 15329 wetting classes and the existing
# crevice_corrosion_ruleset.json environment table.


class EnvironmentClass(str, Enum):
    T0_DRY = "T0_dry"  # <50% RH, indoor heated
    T1_INDOOR_DAMP = "T1_indoor_damp"  # 50-80% RH, indoor unheated
    T2_HUMID = "T2_humid"  # >80% RH or condensing
    T3_CHLORIDE = "T3_chloride"  # pool halls, coastal <5km
    T4_MARINE = "T4_marine"  # direct spray zone
    T5_INDUSTRIAL = "T5_industrial"  # aggressive chemical atmosphere
    UNCLASSIFIED = "unclassified"


# ---------------------------------------------------------------------------
# Piping system classification
# ---------------------------------------------------------------------------
# Determines which corrosion rules apply, what centre-to-centre spacing
# is required, which seismic bracing mass class is used, and what
# operator access patterns apply. Extend as needed; add new members at
# the end and never reorder.


class PipingSystem(str, Enum):
    DOMESTIC_COLD_WATER = "domestic_cold_water"
    DOMESTIC_HOT_WATER = "domestic_hot_water"
    DOMESTIC_HOT_WATER_RETURN = "domestic_hot_water_return"
    CHILLED_WATER_FLOW = "chilled_water_flow"
    CHILLED_WATER_RETURN = "chilled_water_return"
    HEATING_FLOW = "heating_flow"
    HEATING_RETURN = "heating_return"
    CONDENSER_WATER = "condenser_water"
    MEDICAL_GAS_OXYGEN = "medical_gas_oxygen"
    MEDICAL_GAS_NITROUS = "medical_gas_nitrous"
    MEDICAL_GAS_VACUUM = "medical_gas_vacuum"
    MEDICAL_GAS_COMPRESSED_AIR = "medical_gas_compressed_air"
    NATURAL_GAS = "natural_gas"
    COMPRESSED_AIR = "compressed_air"
    STEAM_LP = "steam_lp"
    STEAM_HP = "steam_hp"
    CONDENSATE_RETURN = "condensate_return"
    FOUL_DRAINAGE = "foul_drainage"
    RAINWATER = "rainwater"
    POOL_CHEMICAL_DOSING = "pool_chemical_dosing"
    POOL_CIRCULATION = "pool_circulation"
    FIRE_WET_RISER = "fire_wet_riser"
    FIRE_SPRINKLER = "fire_sprinkler"
    UNKNOWN = "unknown"


# ---------------------------------------------------------------------------
# Joint type classification
# ---------------------------------------------------------------------------
# Keys match JT-001 through JT-014 in crevice_corrosion_ruleset.json.
# See that file for geometry class assignment (open, moderate, tight, critical).


class JointType(str, Enum):
    JT001_PLAIN_WELDED = "JT-001_plain_welded"
    JT002_SOCKET_WELDED = "JT-002_socket_welded"
    JT003_THREADED = "JT-003_threaded"
    JT004_FLANGED_FULL_GASKET = "JT-004_flanged_full_gasket"
    JT005_FLANGED_RING_GASKET = "JT-005_flanged_ring_gasket"
    JT006_COMPRESSION = "JT-006_compression"
    JT007_GROOVED_COUPLING = "JT-007_grooved_coupling"
    JT008_PRESS_FIT = "JT-008_press_fit"
    JT009_SOLDERED = "JT-009_soldered"
    JT010_BRAZED = "JT-010_brazed"
    JT011_MECHANICAL_CLAMP = "JT-011_mechanical_clamp"
    JT012_FUSION_WELDED_PLASTIC = "JT-012_fusion_welded_plastic"
    JT013_PUSH_FIT = "JT-013_push_fit"
    JT014_DIELECTRIC_UNION = "JT-014_dielectric_union"
    UNKNOWN = "unknown"


# ---------------------------------------------------------------------------
# Element subtypes
# ---------------------------------------------------------------------------
# Discriminator for which comparators apply and what the geometry means.
# pipe_segment and fitting carry a Centerline; equipment subtypes do not.

ElementSubtype = Literal[
    "pipe_segment",  # IfcFlowSegment — straight or curved pipe run
    "fitting",  # elbow, tee, reducer, bend
    "valve",  # gate, ball, butterfly, check, etc
    "flange",  # standalone flange pair or blind flange
    "pump",  # centrifugal, inline, submersible
    "tank",  # buffer, expansion, calorifier
    "ahu",  # air handling unit with piping connections
    "fcu",  # fan coil unit
    "strainer",  # y-strainer, basket strainer
    "filter",  # cartridge, bag, media
    "meter",  # flow, pressure, temperature meter
    "heat_exchanger",  # plate, shell-and-tube
    "manifold",  # multi-port assembly
    "support",  # clamp, hanger (relevant for spatial)
    "other",
]


# ---------------------------------------------------------------------------
# Geometry primitives
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class Point3D:
    """A point in world coordinates. Units: metres."""

    x: float
    y: float
    z: float


@dataclass(frozen=True)
class BoundingBox:
    """Axis-aligned bounding box in world coordinates. Units: metres."""

    min: Point3D
    max: Point3D

    @property
    def dimensions_m(self) -> tuple[float, float, float]:
        return (
            self.max.x - self.min.x,
            self.max.y - self.min.y,
            self.max.z - self.min.z,
        )


@dataclass
class Centerline:
    """
    Ordered vertices defining a piping centerline path.

    For a straight pipe, two points. For a curved run (fitting, bent pipe),
    multiple points. Units: metres.
    """

    points: list[Point3D]

    @property
    def total_length_m(self) -> float:
        if len(self.points) < 2:
            return 0.0
        total = 0.0
        for i in range(len(self.points) - 1):
            p1, p2 = self.points[i], self.points[i + 1]
            total += ((p2.x - p1.x) ** 2 + (p2.y - p1.y) ** 2 + (p2.z - p1.z) ** 2) ** 0.5
        return total


# ---------------------------------------------------------------------------
# The main schema
# ---------------------------------------------------------------------------


@dataclass
class PipingElement:
    """
    A single piping element extracted from an IFC model, normalised for
    compliance checking.

    Every piping-related IFC entity becomes one PipingElement. Valves,
    flanges, pumps, AHUs, strainers — all become PipingElement with
    different `subtype` values. Pipe segments additionally carry a
    centerline.
    """

    # --- Identity (always required) ---
    id: str  # IFC GUID
    ifc_class: str  # e.g. "IfcFlowSegment"
    subtype: ElementSubtype
    name: Optional[str] = None  # human-readable IFC Name

    # --- Spatial (required for all spatial comparators) ---
    bbox: Optional[BoundingBox] = None
    centroid: Optional[Point3D] = None
    centerline: Optional[Centerline] = None  # pipe_segment / fitting only
    orientation_vector: Optional[Point3D] = None  # unit vector for directional equipment

    # --- Containment ---
    level_id: Optional[str] = None  # IfcBuildingStorey GUID
    level_name: Optional[str] = None  # "L01 Plant room"
    space_id: Optional[str] = None  # IfcSpace GUID
    space_name: Optional[str] = None
    zone_ids: list[str] = field(default_factory=list)

    # --- Material (required for corrosion comparators) ---
    material: str = "Unknown"  # must be in CANONICAL_MATERIALS
    material_raw: Optional[str] = None  # original IFC string for debugging
    coating: Optional[str] = None  # "galvanised_zinc_60um", "epoxy_powder"
    pren: Optional[float] = None  # overrides rulepack default if set

    # --- Piping geometry ---
    nominal_diameter_mm: Optional[float] = None  # DN
    outside_diameter_mm: Optional[float] = None  # OD
    wall_thickness_mm: Optional[float] = None
    insulation_thickness_mm: Optional[float] = None
    insulation_material: Optional[str] = None

    # --- Service ---
    system: PipingSystem = PipingSystem.UNKNOWN
    operating_temperature_c: Optional[float] = None
    design_pressure_bar: Optional[float] = None

    # --- Environment (required for corrosion comparators) ---
    environment_class: EnvironmentClass = EnvironmentClass.UNCLASSIFIED
    environment_source: Optional[str] = None  # "space_metadata" / "zone" / "manual"

    # --- Joints (for crevice and clearance) ---
    joint_type: Optional[JointType] = None
    joined_to: list[str] = field(default_factory=list)  # GUIDs of neighbouring elements

    # --- Mass (for seismic bracing reservation) ---
    mass_empty_kg: Optional[float] = None
    mass_filled_kg: Optional[float] = None  # with operating fluid

    # --- Operator access (for clearance comparators) ---
    requires_operator_access: bool = False
    access_direction: Optional[Point3D] = None  # unit vector
    access_clearance_required_m: Optional[float] = None  # rulepack default usually wins

    # --- Surface area (for galvanic area-ratio calculation) ---
    wetted_surface_area_m2: Optional[float] = None
    exposed_surface_area_m2: Optional[float] = None

    # --- Raw IFC properties (escape hatch for comparator-specific lookups) ---
    properties: dict = field(default_factory=dict)  # Pset_* key-values

    # --- Extraction provenance ---
    extraction_warnings: list[str] = field(default_factory=list)


# ---------------------------------------------------------------------------
# Validation
# ---------------------------------------------------------------------------


def validate(element: PipingElement) -> list[str]:
    """
    Return a list of validation issues for an element, empty if valid.

    This is a pre-compliance sanity check — it catches schema violations,
    not compliance failures. Run on every PipingElement before passing to
    comparators. Comparators may also call this to decide whether to skip
    an element.
    """
    issues: list[str] = []

    if not element.id:
        issues.append("id is required")
    if not element.ifc_class:
        issues.append("ifc_class is required")
    if element.material not in CANONICAL_MATERIALS:
        issues.append(f"material '{element.material}' not in CANONICAL_MATERIALS")
    if element.subtype in ("pipe_segment", "fitting") and element.centerline is None:
        issues.append(f"subtype '{element.subtype}' requires a centerline")
    if element.subtype in ("pipe_segment",) and element.nominal_diameter_mm is None:
        issues.append("pipe_segment requires nominal_diameter_mm")

    # Cross-field consistency
    if (
        element.mass_filled_kg is not None
        and element.mass_empty_kg is not None
        and element.mass_filled_kg < element.mass_empty_kg
    ):
        issues.append("mass_filled_kg < mass_empty_kg")

    return issues


# ---------------------------------------------------------------------------
# JSON serialisation
# ---------------------------------------------------------------------------


def to_dict(element: PipingElement) -> dict[str, Any]:
    """Convert a PipingElement to a plain dict (JSON-serialisable)."""
    return asdict(element)


def to_json(element: PipingElement, indent: Optional[int] = 2) -> str:
    """Convert a PipingElement to JSON. Enums serialise as their string value."""
    return json.dumps(to_dict(element), indent=indent, default=_json_default)


def _json_default(obj: Any) -> Any:
    if isinstance(obj, Enum):
        return obj.value
    if is_dataclass(obj):
        return asdict(obj)
    raise TypeError(f"Not JSON serialisable: {type(obj).__name__}")


# ---------------------------------------------------------------------------
# Example instances — canonical fixtures for tests and demos
# ---------------------------------------------------------------------------


def example_ss316_pipe_in_plant_room() -> PipingElement:
    """A stainless 316 header pipe in a chlorinated plant room atmosphere."""
    return PipingElement(
        id="3Kf7q8XzR1pP2mN4gV8xQ",
        ifc_class="IfcFlowSegment",
        subtype="pipe_segment",
        name="Pool circulation header H1",
        bbox=BoundingBox(
            min=Point3D(x=2.0, y=1.0, z=3.45),
            max=Point3D(x=18.0, y=1.1, z=3.55),
        ),
        centroid=Point3D(x=10.0, y=1.05, z=3.5),
        centerline=Centerline(
            points=[
                Point3D(x=2.0, y=1.0, z=3.5),
                Point3D(x=18.0, y=1.0, z=3.5),
            ]
        ),
        level_id="1Kf7q8XzR1pP2mN4gV8xQ",
        level_name="L01 Plant room",
        space_id="2Wn7q8XzR1pP2mN4gV8xQ",
        space_name="POOL-PLT-01",
        material="SS316",
        material_raw="Stainless Steel, Grade 316",
        pren=25.2,
        nominal_diameter_mm=150.0,
        outside_diameter_mm=168.3,
        wall_thickness_mm=3.4,
        insulation_thickness_mm=25.0,
        insulation_material="phenolic_foam",
        system=PipingSystem.POOL_CIRCULATION,
        operating_temperature_c=28.0,
        design_pressure_bar=6.0,
        environment_class=EnvironmentClass.T3_CHLORIDE,
        environment_source="space_metadata",
        joint_type=JointType.JT004_FLANGED_FULL_GASKET,
        joined_to=["4Hj7q8XzR1pP2mN4gV8xQ", "5Gp7q8XzR1pP2mN4gV8xQ"],
        mass_empty_kg=220.0,
        mass_filled_kg=510.0,
        wetted_surface_area_m2=8.45,
        exposed_surface_area_m2=8.45,
    )


def example_valve() -> PipingElement:
    """A DN80 ball valve requiring operator access."""
    return PipingElement(
        id="6Qj7q8XzR1pP2mN4gV8xQ",
        ifc_class="IfcValve",
        subtype="valve",
        name="BV-04 isolation",
        bbox=BoundingBox(
            min=Point3D(x=9.85, y=0.95, z=3.40),
            max=Point3D(x=10.15, y=1.15, z=3.70),
        ),
        centroid=Point3D(x=10.0, y=1.05, z=3.55),
        orientation_vector=Point3D(x=0.0, y=-1.0, z=0.0),  # handwheel faces -Y
        level_name="L01 Plant room",
        material="SS316",
        material_raw="316 SS",
        pren=25.2,
        nominal_diameter_mm=80.0,
        system=PipingSystem.POOL_CIRCULATION,
        operating_temperature_c=28.0,
        design_pressure_bar=6.0,
        environment_class=EnvironmentClass.T3_CHLORIDE,
        environment_source="space_metadata",
        joint_type=JointType.JT004_FLANGED_FULL_GASKET,
        mass_empty_kg=18.5,
        mass_filled_kg=19.2,
        requires_operator_access=True,
        access_direction=Point3D(x=0.0, y=-1.0, z=0.0),
        access_clearance_required_m=0.6,
    )


def example_pump() -> PipingElement:
    """A horizontal centrifugal circulation pump on the plant room floor."""
    return PipingElement(
        id="7Km7q8XzR1pP2mN4gV8xQ",
        ifc_class="IfcPump",
        subtype="pump",
        name="PUMP-04 pool circulation",
        bbox=BoundingBox(
            min=Point3D(x=9.2, y=3.2, z=0.1),
            max=Point3D(x=10.8, y=4.4, z=0.9),
        ),
        centroid=Point3D(x=10.0, y=3.8, z=0.5),
        orientation_vector=Point3D(x=1.0, y=0.0, z=0.0),  # discharge +X
        level_name="L01 Plant room",
        material="SS304",
        material_raw="Stainless Steel 304",
        pren=18.0,
        coating="epoxy_powder",
        system=PipingSystem.POOL_CIRCULATION,
        operating_temperature_c=28.0,
        design_pressure_bar=6.0,
        environment_class=EnvironmentClass.T3_CHLORIDE,
        environment_source="space_metadata",
        mass_empty_kg=145.0,
        mass_filled_kg=162.0,
        requires_operator_access=True,
        access_direction=Point3D(x=0.0, y=-1.0, z=0.0),
        access_clearance_required_m=1.0,
    )


if __name__ == "__main__":
    # Smoke test — validate the examples and print one as JSON
    for ex in (
        example_ss316_pipe_in_plant_room(),
        example_valve(),
        example_pump(),
    ):
        problems = validate(ex)
        assert not problems, f"Example invalid: {ex.name} — {problems}"
    print(f"piping_schema.py v{SCHEMA_VERSION} — all examples valid")
    print(to_json(example_ss316_pipe_in_plant_room()))
