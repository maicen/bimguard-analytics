"""
ifc_quality/improver.py
------------------------
Adds missing GUIDs, names, and default property sets to low-quality IFC files.

Usage:
    from app.modules.ifc_quality.improver import improve_ifc_file

    improve_ifc_file("original.ifc", "improved.ifc")
"""

import uuid
from typing import Dict

try:
    import ifcopenshell
    from ifcopenshell.util.element import get_psets
    from ifcopenshell.api import run
    _IFC_AVAILABLE = True
except ImportError:
    _IFC_AVAILABLE = False

_DEFAULT_PSETS: dict = {
    "IfcWall": {
        "Pset_WallCommon": {
            "LoadBearing": False, "FireRating": "0",
            "AcousticRating": "0dB", "Thickness": 0.15,
        }
    },
    "IfcDoor": {
        "Pset_DoorCommon": {
            "FireRating": "0", "SmokeStop": False,
            "IsExternal": False, "Acoustic": "0dB",
        }
    },
    "IfcWindow": {
        "Pset_WindowCommon": {
            "FireRating": "0", "IsExternal": False,
            "Acoustic": "0dB", "ThermalTransmittance": 3.0,
        }
    },
    "IfcSpace": {
        "Pset_SpaceCommon": {
            "GrossFloorArea": 0.0, "NetFloorArea": 0.0,
            "OccupancyType": "Unknown",
        }
    },
    "IfcSlab": {
        "Pset_SlabCommon": {
            "FireRating": "0", "AcousticRating": "0dB", "Thickness": 0.25,
        }
    },
    "IfcRoof": {
        "Pset_RoofCommon": {"FireRating": "0", "PitchAngle": 0.0}
    },
}


class IFCImprover:
    """Enhance IFC file quality by adding missing GUIDs, names, and properties."""

    def __init__(self, input_filepath: str):
        if not _IFC_AVAILABLE:
            raise ImportError("ifcopenshell is not installed")
        self.input_path = input_filepath
        self.ifc = ifcopenshell.open(input_filepath)
        self._log: list[str] = []

    def improve_all(self) -> Dict:
        self._add_missing_guids()
        self._add_missing_names()
        self._add_default_properties()
        return self._build_summary()

    def save(self, output_filepath: str):
        self.ifc.write(output_filepath)
        print(f"Improved file saved: {output_filepath}")

    # ── Steps ─────────────────────────────────────────────────────────────────

    def _add_missing_guids(self):
        added = 0
        for el in self.ifc.entities:
            if hasattr(el, "GlobalId"):
                if not el.GlobalId or not str(el.GlobalId).strip():
                    el.GlobalId = str(uuid.uuid4()).replace("-", "")[:22]
                    added += 1
        msg = f"GUIDs added: {added}"
        print(msg); self._log.append(msg)

    def _add_missing_names(self):
        added = 0
        counts: dict = {}
        for el in self.ifc.entities:
            if hasattr(el, "Name"):
                if not el.Name or not str(el.Name).strip():
                    t = el.is_a()
                    counts[t] = counts.get(t, 0) + 1
                    el.Name = f"{t}_{counts[t]:03d}"
                    added += 1
        msg = f"Names added: {added}"
        print(msg); self._log.append(msg)

    def _add_default_properties(self):
        added = 0
        for el in self.ifc.entities:
            t = el.is_a()
            if t not in _DEFAULT_PSETS:
                continue
            try:
                psets = get_psets(el, psets_only=False)
            except Exception:
                psets = {}
            if not psets:
                for ps_name, props in _DEFAULT_PSETS[t].items():
                    try:
                        pset = run("pset.new_pset", self.ifc, ifc_class=t, name=ps_name)
                        run("pset.edit_pset", self.ifc, pset=pset, properties=props)
                        added += 1
                    except Exception:
                        pass
        msg = f"Property sets added: {added}"
        print(msg); self._log.append(msg)

    def _build_summary(self) -> Dict:
        total = len(list(self.ifc.entities))
        with_guid = sum(
            1 for e in self.ifc.entities
            if hasattr(e, "GlobalId") and e.GlobalId
        )
        with_name = sum(
            1 for e in self.ifc.entities
            if hasattr(e, "Name") and e.Name
        )
        with_props = 0
        for el in self.ifc.entities:
            try:
                if get_psets(el, psets_only=False):
                    with_props += 1
            except Exception:
                pass
        return {
            "total_elements": total,
            "with_guid":       with_guid,
            "with_name":       with_name,
            "with_properties": with_props,
            "improvements":    self._log,
        }


def improve_ifc_file(input_path: str, output_path: str | None = None) -> Dict:
    if output_path is None:
        output_path = input_path.replace(".ifc", "_improved.ifc")
    improver = IFCImprover(input_path)
    summary = improver.improve_all()
    improver.save(output_path)
    return summary


if __name__ == "__main__":
    import sys
    if len(sys.argv) < 2:
        print("Usage: python improver.py <input.ifc> [output.ifc]")
        sys.exit(1)
    improve_ifc_file(sys.argv[1], sys.argv[2] if len(sys.argv) > 2 else None)
