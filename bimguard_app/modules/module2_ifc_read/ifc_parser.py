"""
BIMGUARD AI — IFC Parser Module
OpenBIM compliant: reads any IFC 2x3 or IFC4 file regardless of authoring tool.
Standard: ISO 16739-1
Library:  ifcopenshell (open source)
"""

import uuid
from dataclasses import dataclass
from typing import Optional

import ifcopenshell
import ifcopenshell.util.element
import ifcopenshell.util.placement


@dataclass
class ServiceElement:
    """Represents one MEP service element extracted from the IFC model."""

    guid: str
    name: str
    ifc_type: str
    description: str
    material_a: str
    material_b: Optional[str]
    location_tag: str
    floor: str
    system: str
    joint_type: str
    anode_area_m2: float
    cathode_area_m2: float
    position: tuple  # (x, y, z) in metres
    length_m: float
    notes: str = ""


# Mapping from IFC type to plain English service category
IFC_SERVICE_LABELS = {
    "IfcPipeSegment": "Pipework",
    "IfcPipeFitting": "Pipe fitting",
    "IfcFlowFitting": "Flow fitting",
    "IfcValve": "Valve",
    "IfcPump": "Pump",
    "IfcHeatExchanger": "Heat exchanger",
    "IfcDistributionElement": "Distribution element",
    "IfcMember": "Structural member",
    "IfcPlate": "Structural plate",
    "IfcFastener": "Fastener / fixing",
    "IfcCableSegment": "Cable",
    "IfcDuctSegment": "Ductwork",
    "IfcDuctFitting": "Duct fitting",
}

# Infer joint type from IFC element type
IFC_TO_JOINT = {
    "IfcPipeFitting": "JT-001",  # Flanged connections most common
    "IfcFlowFitting": "JT-001",
    "IfcValve": "JT-013",
    "IfcFastener": "JT-010",
    "IfcMember": "JT-005",
    "IfcPlate": "JT-014",
    "IfcHeatExchanger": "JT-009",
    "IfcPipeSegment": "JT-012",  # Pipe clamp connection
}

# Space type → environment class mapping
SPACE_TO_ENV = {
    "pool": "swimming_pool",
    "swimming": "swimming_pool",
    "plant": "interior_conditioned",
    "riser": "interior_conditioned",
    "mechanical": "interior_conditioned",
    "roof": "urban_exterior",
    "facade": "coastal",
    "external": "urban_exterior",
    "coastal": "coastal",
    "marine": "marine_splash",
    "industrial": "industrial",
    "office": "interior_dry",
    "retail": "interior_dry",
    "residential": "interior_dry",
}


def get_material_name(element, ifc_model) -> str:
    """Extract primary material name from an IFC element."""
    try:
        mats = ifcopenshell.util.element.get_materials(element)
        if mats:
            return mats[0].Name if hasattr(mats[0], "Name") else str(mats[0])
    except Exception:
        pass

    # Fallback: check material associations directly
    for rel in getattr(element, "HasAssociations", []):
        if rel.is_a("IfcRelAssociatesMaterial"):
            mat = rel.RelatingMaterial
            if hasattr(mat, "Name"):
                return mat.Name
            if hasattr(mat, "ForLayerSet"):
                layers = mat.ForLayerSet.MaterialLayers
                if layers:
                    return layers[0].Material.Name
    return "Unknown"


def normalise_material_name(raw: str) -> str:
    """Map free-text material names from IFC to BIMGUARD AI material keys."""
    r = raw.lower().strip()
    if "316" in r or "1.4401" in r:
        return "SS_316_passive"
    if "304" in r or "1.4301" in r:
        return "SS_304_passive"
    if "duplex" in r and ("2507" in r or "super" in r):
        return "SS_super_duplex_2507"
    if "duplex" in r or "2205" in r:
        return "SS_duplex_2205"
    if "copper" in r or "cu " in r:
        return "Copper"
    if "brass" in r:
        return "Brass_naval"
    if "galvan" in r or "hdg" in r or "hot dip" in r:
        return "Galvanized_steel"
    if "alumin" in r or "aluminum" in r:
        return "Aluminum_alloy_6063"
    if "carbon steel" in r or "mild steel" in r or "s275" in r or "s355" in r:
        return "Carbon_steel_mild"
    if "cast iron" in r:
        return "Cast_iron"
    if "titanium" in r:
        return "Titanium"
    if "zinc" in r:
        return "Zinc"
    if "lead" in r:
        return "Lead"
    # Default — flag as unknown but don't crash
    return raw.replace(" ", "_")[:30]


def classify_environment_from_space(space_name: str, floor: str) -> str:
    """Infer environment class from space name and floor tag."""
    combined = (space_name + " " + floor).lower()
    for keyword, env in SPACE_TO_ENV.items():
        if keyword in combined:
            return env
    return "interior_dry"


def get_element_position(element, ifc_model) -> tuple:
    """Extract (x, y, z) position in metres from IFC element placement."""
    try:
        mat = ifcopenshell.util.placement.get_local_placement(element.ObjectPlacement)
        return (round(float(mat[0][3]), 2), round(float(mat[1][3]), 2), round(float(mat[2][3]), 2))
    except Exception:
        return (0.0, 0.0, 0.0)


def get_floor_name(element, ifc_model) -> str:
    """Find the storey this element belongs to."""
    for rel in getattr(element, "ContainedInStructure", []):
        container = rel.RelatingStructure
        if container.is_a("IfcBuildingStorey"):
            return container.Name or "Unknown floor"
    return "Unknown floor"


def get_system_name(element, ifc_model) -> str:
    """Find MEP system this element belongs to."""
    for rel in ifc_model.get_inverse(element):
        if rel.is_a("IfcRelAssignsToGroup"):
            group = rel.RelatingGroup
            if group.is_a("IfcSystem") or group.is_a("IfcDistributionSystem"):
                return group.Name or "Unnamed system"
    return "Unassigned"


def parse_ifc(ifc_path: str) -> list[ServiceElement]:
    """
    Main entry point. Parses an IFC file and returns a list of
    ServiceElement objects ready for corrosion compliance checking.

    Args:
        ifc_path: Path to .ifc file (IFC 2x3 or IFC4)

    Returns:
        List of ServiceElement dataclass instances
    """
    model = ifcopenshell.open(ifc_path)
    elements = []

    target_types = list(IFC_SERVICE_LABELS.keys())

    for ifc_type in target_types:
        for el in model.by_type(ifc_type):
            mat_a_raw = get_material_name(el, model)
            mat_a = normalise_material_name(mat_a_raw)
            mat_b = None  # Second material (e.g. bracket material) — extend via Pset

            floor = get_floor_name(el, model)
            system = get_system_name(el, model)

            # Try to get space from containing zone or description
            space_name = ""
            for rel in getattr(el, "ContainedInStructure", []):
                space_name = getattr(rel.RelatingStructure, "Name", "") or ""

            env = classify_environment_from_space(space_name + " " + (el.Name or ""), floor)
            joint = IFC_TO_JOINT.get(ifc_type, "JT-005")
            pos = get_element_position(el, model)

            # Estimate areas (extend with actual geometry extraction)
            anode_area = 0.05
            cathode_area = 0.50

            elements.append(
                ServiceElement(
                    guid=el.GlobalId,
                    name=el.Name or f"{ifc_type}_{el.id()}",
                    ifc_type=ifc_type,
                    description=IFC_SERVICE_LABELS.get(ifc_type, ifc_type),
                    material_a=mat_a,
                    material_b=mat_b,
                    location_tag=env,
                    floor=floor,
                    system=system,
                    joint_type=joint,
                    anode_area_m2=anode_area,
                    cathode_area_m2=cathode_area,
                    position=pos,
                    length_m=1.0,
                )
            )

    return elements


def generate_synthetic_elements(n: int = 25) -> list[ServiceElement]:
    """
    Generates realistic synthetic MEP service elements for demo use
    when no IFC file is available. Covers a range of risk levels,
    environments, and service types — matching real building scenarios.
    """
    import random

    random.seed(42)

    scenarios = [
        # (name, ifc_type, mat_a, mat_b, env, joint, floor, system, aa, ca, pos)
        (
            "CHW Supply Pipe",
            "IfcPipeSegment",
            "SS_316_passive",
            "Galvanized_steel",
            "interior_conditioned",
            "JT-012",
            "B1 Plant Room",
            "Chilled Water",
            0.05,
            0.50,
            (10, 5, 0),
        ),
        (
            "HWS Return Pipe",
            "IfcPipeSegment",
            "Copper",
            "Galvanized_steel",
            "interior_conditioned",
            "JT-012",
            "B1 Plant Room",
            "Hot Water Services",
            0.10,
            0.40,
            (12, 5, 0),
        ),
        (
            "Pool Heating Pipe",
            "IfcPipeSegment",
            "SS_316_passive",
            "SS_316_passive",
            "swimming_pool",
            "JT-001",
            "Pool Level",
            "Pool Heating",
            0.08,
            0.08,
            (5, 20, 0),
        ),
        (
            "Pool Plant Flange",
            "IfcPipeFitting",
            "SS_316_passive",
            None,
            "swimming_pool",
            "JT-001",
            "Pool Level",
            "Pool Heating",
            0.02,
            0.02,
            (5, 22, 0),
        ),
        (
            "Coastal Facade Fix",
            "IfcFastener",
            "Aluminum_alloy_6063",
            "SS_316_passive",
            "coastal",
            "JT-010",
            "Level 3",
            "Facade",
            0.002,
            0.85,
            (30, 0, 9),
        ),
        (
            "Roof Drainage Fix",
            "IfcFastener",
            "Galvanized_steel",
            "SS_316_passive",
            "urban_exterior",
            "JT-010",
            "Roof",
            "Drainage",
            0.03,
            0.50,
            (15, 15, 12),
        ),
        (
            "Structural Bracket",
            "IfcMember",
            "Carbon_steel_mild",
            "SS_316_passive",
            "urban_exterior",
            "JT-005",
            "Level 1",
            "Structure",
            0.15,
            0.40,
            (8, 8, 3),
        ),
        (
            "Cold Water Feed",
            "IfcPipeSegment",
            "Copper",
            "Cast_iron",
            "interior_dry",
            "JT-003",
            "Ground Floor",
            "CWS",
            0.50,
            0.20,
            (4, 4, 0),
        ),
        (
            "SS Pipe Clamp",
            "IfcPipeSegment",
            "SS_316_passive",
            None,
            "interior_conditioned",
            "JT-011",
            "B1 Plant Room",
            "Chilled Water",
            0.10,
            0.10,
            (11, 6, 0),
        ),
        (
            "Unlined Pipe Clamp",
            "IfcPipeSegment",
            "SS_316_passive",
            "Carbon_steel_mild",
            "coastal",
            "JT-012",
            "Roof",
            "External Services",
            0.05,
            0.20,
            (20, 20, 12),
        ),
        (
            "HX Tube Joint",
            "IfcHeatExchanger",
            "SS_316_passive",
            None,
            "swimming_pool",
            "JT-009",
            "Pool Level",
            "Pool Heating",
            0.01,
            0.50,
            (6, 21, 0),
        ),
        (
            "Drainage Transition",
            "IfcPipeFitting",
            "Cast_iron",
            "Copper",
            "interior_dry",
            "JT-002",
            "Ground Floor",
            "Drainage",
            0.50,
            0.20,
            (3, 3, 0),
        ),
        (
            "Gas Pipe Riser",
            "IfcPipeSegment",
            "Carbon_steel_mild",
            "Galvanized_steel",
            "interior_conditioned",
            "JT-003",
            "Riser Shaft",
            "Gas",
            0.30,
            0.30,
            (7, 7, 6),
        ),
        (
            "Marine Plant Pipe",
            "IfcPipeSegment",
            "SS_316_passive",
            None,
            "marine_splash",
            "JT-001",
            "Ground Floor",
            "Marine Services",
            0.10,
            0.10,
            (25, 5, 0),
        ),
        (
            "Electrical Tray",
            "IfcDistributionElement",
            "Aluminum_alloy_6063",
            "Carbon_steel_mild",
            "interior_conditioned",
            "JT-005",
            "Level 1",
            "Electrical",
            0.80,
            0.20,
            (9, 2, 3),
        ),
        (
            "Vent Duct Bracket",
            "IfcDuctSegment",
            "Galvanized_steel",
            "Carbon_steel_mild",
            "interior_dry",
            "JT-005",
            "Level 2",
            "Ventilation",
            0.60,
            0.30,
            (6, 10, 6),
        ),
        (
            "Condenser Pipe",
            "IfcPipeSegment",
            "Copper",
            "Aluminum_alloy_6063",
            "urban_exterior",
            "JT-012",
            "Roof",
            "Cooling",
            0.08,
            0.30,
            (18, 18, 12),
        ),
        (
            "Fix Plate Coastal",
            "IfcPlate",
            "SS_316_passive",
            None,
            "coastal",
            "JT-014",
            "Level 3",
            "Facade",
            0.02,
            0.02,
            (31, 1, 9),
        ),
        (
            "Sprinkler Header",
            "IfcPipeSegment",
            "Carbon_steel_mild",
            "SS_316_passive",
            "interior_conditioned",
            "JT-001",
            "Level 1",
            "Fire Protection",
            0.10,
            0.50,
            (10, 10, 3),
        ),
        (
            "Threaded SS Riser",
            "IfcPipeSegment",
            "SS_304_passive",
            None,
            "interior_conditioned",
            "JT-003",
            "Riser Shaft",
            "Domestic Hot Water",
            0.05,
            0.05,
            (7, 8, 3),
        ),
        (
            "Pool Valve Body",
            "IfcValve",
            "SS_304_passive",
            None,
            "swimming_pool",
            "JT-013",
            "Pool Level",
            "Pool Heating",
            0.03,
            0.03,
            (5, 23, 0),
        ),
        (
            "Industrial Flange",
            "IfcPipeFitting",
            "SS_316_passive",
            None,
            "industrial",
            "JT-001",
            "Ground Floor",
            "Process",
            0.04,
            0.04,
            (22, 8, 0),
        ),
        (
            "Lead Flashing Fix",
            "IfcFastener",
            "Aluminum_alloy_6063",
            "Lead",
            "urban_exterior",
            "JT-010",
            "Roof",
            "Weathering",
            0.30,
            0.10,
            (14, 14, 12),
        ),
        (
            "Bronze Valve",
            "IfcValve",
            "Bronze",
            "Copper",
            "interior_dry",
            "JT-013",
            "Ground Floor",
            "CWS",
            0.05,
            0.30,
            (3, 5, 0),
        ),
        (
            "Stainless Header",
            "IfcPipeSegment",
            "SS_316_passive",
            "SS_316_passive",
            "urban_exterior",
            "JT-002",
            "Roof",
            "Cooling",
            0.20,
            0.20,
            (19, 19, 12),
        ),
    ]

    elements = []
    for i, sc in enumerate(scenarios[:n]):
        name, ifc_type, mat_a, mat_b, env, joint, floor, system, aa, ca, pos = sc
        elements.append(
            ServiceElement(
                guid=str(uuid.uuid4()).upper()[:22],
                name=name,
                ifc_type=ifc_type,
                description=IFC_SERVICE_LABELS.get(ifc_type, ifc_type),
                material_a=mat_a,
                material_b=mat_b or mat_a,
                location_tag=env,
                floor=floor,
                system=system,
                joint_type=joint,
                anode_area_m2=aa,
                cathode_area_m2=ca,
                position=pos,
                length_m=round(random.uniform(0.5, 8.0), 1),
            )
        )
    return elements
