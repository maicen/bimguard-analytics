"""
ifc_quality/generator.py
-------------------------
Creates well-formed IFC test files with proper hierarchy, GUIDs, names,
and property sets — ready for Module 2 compliance extraction.

Usage:
    from app.modules.ifc_quality.generator import generate_compliance_test_file

    path = generate_compliance_test_file("test_compliance.ifc")
"""

from typing import Dict

try:
    import ifcopenshell
    from ifcopenshell.api import run
    _IFC_AVAILABLE = True
except ImportError:
    _IFC_AVAILABLE = False


class IFCTestGenerator:
    """Build well-formed IFC test files programmatically."""

    def __init__(self, schema: str = "IFC4"):
        if not _IFC_AVAILABLE:
            raise ImportError("ifcopenshell is not installed")
        self.schema = schema
        self.ifc = None
        self.owner_history = None
        self.storey = None

    def create_base_file(self, project_name: str = "Test Building"):
        self.ifc = ifcopenshell.file(schema=self.schema)
        self.owner_history = run("owner.create_owner_history", self.ifc)
        project = run("root.create_element", self.ifc, ifc_class="IfcProject")
        project.Name = project_name
        project.OwnerHistory = self.owner_history
        site = run("root.create_element", self.ifc, ifc_class="IfcSite")
        site.Name = "Test Site"
        site.OwnerHistory = self.owner_history
        run("aggregate.assign_object", self.ifc,
            relating_object=project, related_object=site)
        building = run("root.create_element", self.ifc, ifc_class="IfcBuilding")
        building.Name = "Test Building"
        building.OwnerHistory = self.owner_history
        run("aggregate.assign_object", self.ifc,
            relating_object=site, related_object=building)
        self.storey = run("root.create_element", self.ifc, ifc_class="IfcBuildingStorey")
        self.storey.Name = "Ground Floor"
        self.storey.OwnerHistory = self.owner_history
        run("aggregate.assign_object", self.ifc,
            relating_object=building, related_object=self.storey)
        return self.ifc

    # ── Element helpers ───────────────────────────────────────────────────────

    def add_wall(self, name: str, guid: str | None = None,
                 properties: Dict | None = None):
        el = run("root.create_element", self.ifc, ifc_class="IfcWall")
        el.Name = name
        el.OwnerHistory = self.owner_history
        if guid:
            el.GlobalId = guid
        run("aggregate.assign_object", self.ifc,
            relating_object=self.storey, related_object=el)
        self._add_properties(el, properties or {
            "Pset_WallCommon": {
                "LoadBearing": True, "FireRating": "60",
                "AcousticRating": "50dB", "Thickness": 0.2,
            }
        })
        return el

    def add_door(self, name: str, guid: str | None = None,
                 properties: Dict | None = None):
        el = run("root.create_element", self.ifc, ifc_class="IfcDoor")
        el.Name = name
        el.OverallHeight = 2.1
        el.OverallWidth = 0.9
        el.OwnerHistory = self.owner_history
        if guid:
            el.GlobalId = guid
        run("aggregate.assign_object", self.ifc,
            relating_object=self.storey, related_object=el)
        self._add_properties(el, properties or {
            "Pset_DoorCommon": {
                "FireRating": "30", "SmokeStop": False,
                "IsExternal": False, "Acoustic": "30dB",
            }
        })
        return el

    def add_window(self, name: str, guid: str | None = None,
                   properties: Dict | None = None):
        el = run("root.create_element", self.ifc, ifc_class="IfcWindow")
        el.Name = name
        el.OverallHeight = 1.5
        el.OverallWidth = 1.2
        el.OwnerHistory = self.owner_history
        if guid:
            el.GlobalId = guid
        run("aggregate.assign_object", self.ifc,
            relating_object=self.storey, related_object=el)
        self._add_properties(el, properties or {
            "Pset_WindowCommon": {
                "FireRating": "0", "IsExternal": True,
                "Acoustic": "28dB", "ThermalTransmittance": 2.8,
            }
        })
        return el

    def add_space(self, name: str, guid: str | None = None,
                  properties: Dict | None = None):
        el = run("root.create_element", self.ifc, ifc_class="IfcSpace")
        el.Name = name
        el.OwnerHistory = self.owner_history
        if guid:
            el.GlobalId = guid
        run("aggregate.assign_object", self.ifc,
            relating_object=self.storey, related_object=el)
        self._add_properties(el, properties or {
            "Pset_SpaceCommon": {
                "GrossFloorArea": 50.0, "NetFloorArea": 45.0,
                "OccupancyType": "Office",
            }
        })
        return el

    def _add_properties(self, element, properties: Dict):
        for ps_name, props in properties.items():
            try:
                pset = run("pset.new_pset", self.ifc,
                           ifc_class=element.is_a(), name=ps_name)
                run("pset.edit_pset", self.ifc, pset=pset, properties=props)
            except Exception as exc:
                print(f"Warning: could not add {ps_name}: {exc}")

    def save(self, filepath: str):
        self.ifc.write(filepath)
        print(f"Saved: {filepath}")


# ── Convenience functions ─────────────────────────────────────────────────────

def generate_simple_test_file(output_path: str = "test_simple.ifc") -> str:
    gen = IFCTestGenerator()
    gen.create_base_file("Simple Test Building")
    gen.add_wall("Perimeter_Wall_001", "10000000000000000000000000000001")
    gen.add_wall("Perimeter_Wall_002", "10000000000000000000000000000002")
    gen.add_wall("Interior_Wall_001",  "10000000000000000000000000000003")
    gen.add_door("Main_Door_001",      "10000000000000000000000000000004")
    gen.add_door("Emergency_Exit_001", "10000000000000000000000000000005")
    gen.add_window("Window_North_001", "10000000000000000000000000000006")
    gen.add_window("Window_South_001", "10000000000000000000000000000007")
    gen.add_space("Office_A",          "10000000000000000000000000000008")
    gen.add_space("Meeting_Room_B",    "10000000000000000000000000000009")
    gen.save(output_path)
    return output_path


def generate_compliance_test_file(output_path: str = "test_compliance.ifc") -> str:
    gen = IFCTestGenerator()
    gen.create_base_file("Compliance Test Building")

    # Walls — three fire-rating scenarios
    gen.add_wall("FireRated_Wall_60min",  "20000000000000000000000000000001",
                 {"Pset_WallCommon": {"FireRating": "60",  "LoadBearing": True,  "Thickness": 0.25}})
    gen.add_wall("FireRated_Wall_120min", "20000000000000000000000000000002",
                 {"Pset_WallCommon": {"FireRating": "120", "LoadBearing": True,  "Thickness": 0.3}})
    gen.add_wall("NonFireRated_Wall",     "20000000000000000000000000000003",
                 {"Pset_WallCommon": {"FireRating": "0",   "LoadBearing": False, "Thickness": 0.1}})

    # Doors
    gen.add_door("FireDoor_30min", "20000000000000000000000000000004",
                 {"Pset_DoorCommon": {"FireRating": "30", "SmokeStop": True,  "IsExternal": False}})
    gen.add_door("FireDoor_60min", "20000000000000000000000000000005",
                 {"Pset_DoorCommon": {"FireRating": "60", "SmokeStop": True,  "IsExternal": False}})
    gen.add_door("RegularDoor",    "20000000000000000000000000000006",
                 {"Pset_DoorCommon": {"FireRating": "0",  "SmokeStop": False, "IsExternal": False}})

    # Windows with acoustic ratings
    gen.add_window("AcousticWindow", "20000000000000000000000000000007",
                   {"Pset_WindowCommon": {"Acoustic": "40dB", "IsExternal": True, "ThermalTransmittance": 1.4}})
    gen.add_window("StandardWindow", "20000000000000000000000000000008",
                   {"Pset_WindowCommon": {"Acoustic": "28dB", "IsExternal": True, "ThermalTransmittance": 2.8}})

    # Spaces with area constraints
    gen.add_space("Large_Office", "20000000000000000000000000000009",
                  {"Pset_SpaceCommon": {"GrossFloorArea": 150.0, "NetFloorArea": 140.0, "OccupancyType": "Office"}})
    gen.add_space("Small_Office", "20000000000000000000000000000010",
                  {"Pset_SpaceCommon": {"GrossFloorArea": 25.0,  "NetFloorArea": 22.0,  "OccupancyType": "Office"}})

    gen.save(output_path)
    return output_path


if __name__ == "__main__":
    generate_simple_test_file("test_simple.ifc")
    generate_compliance_test_file("test_compliance.ifc")
    print("Test files generated.")
