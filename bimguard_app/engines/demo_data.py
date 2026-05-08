"""
BIMGUARD AI — Synthetic Demo Dataset
demo_data.py

Generates 25 synthetic MEP pipe elements representing a typical
commercial building plant room and distribution system.
Used when no IFC file is uploaded.
"""

import os
import sys

# Add parent directory to path for engine imports
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

try:
    from engines.bimguard_corrosion_engine import GCElement, assess_galvanic_risk
    from engines.bimguard_crevice_engine import CCElement, assess_crevice_risk
    from engines.bimguard_mic_engine import MICElement, assess_mic_risk

    ENGINES_AVAILABLE = True
except ImportError:
    ENGINES_AVAILABLE = False

# ── SYNTHETIC ELEMENT DEFINITIONS ────────────────────────────────────────────
DEMO_ELEMENTS = [
    # Critical galvanic — copper/galvanised in humid plant room
    {
        "id": "BG-001",
        "type": "IfcPipeSegment",
        "service": "Chilled Water",
        "floor": "B1",
        "zone": "Plant Room",
        "mat_a": "copper",
        "mat_b": "galv_steel",
        "area_a": 2.5,
        "area_b": 12.0,
        "joint": "weld neck flange",
        "temp": 12.0,
        "velocity": 0.45,
        "dead_leg": 0.0,
        "x": 1.2,
        "y": 0.5,
        "z": 3.1,
    },
    # Critical crevice — SS316 flanged in pool
    {
        "id": "BG-002",
        "type": "IfcPipeSegment",
        "service": "Pool Plant",
        "floor": "B1",
        "zone": "Pool Plant Room",
        "mat_a": "SS 316",
        "mat_b": "SS 316",
        "area_a": 3.1,
        "area_b": 3.1,
        "joint": "weld neck flange",
        "temp": 35.0,
        "velocity": 0.3,
        "dead_leg": 0.0,
        "x": 3.4,
        "y": 1.2,
        "z": 2.8,
    },
    # Critical MIC — carbon steel fire suppression dead-leg
    {
        "id": "BG-003",
        "type": "IfcPipeSegment",
        "service": "Fire Suppression",
        "floor": "B2",
        "zone": "Car Park",
        "mat_a": "carbon_steel",
        "mat_b": "carbon_steel",
        "area_a": 4.2,
        "area_b": 4.2,
        "joint": "butt weld",
        "temp": 22.0,
        "velocity": 0.0,
        "dead_leg": 8.0,
        "x": 5.1,
        "y": 2.3,
        "z": 2.5,
    },
    # High galvanic — aluminium/SS316 in humid plant room
    {
        "id": "BG-004",
        "type": "IfcPipeSegment",
        "service": "LTHW",
        "floor": "B1",
        "zone": "Plant Room",
        "mat_a": "aluminium",
        "mat_b": "ss316_passive",
        "area_a": 1.8,
        "area_b": 6.5,
        "joint": "slip-on flange",
        "temp": 75.0,
        "velocity": 0.8,
        "dead_leg": 0.0,
        "x": 2.1,
        "y": 3.4,
        "z": 3.0,
    },
    # High crevice — SS304 compression fitting in normal environment
    {
        "id": "BG-005",
        "type": "IfcPipeFitting",
        "service": "Domestic Cold Water",
        "floor": "01",
        "zone": "Office",
        "mat_a": "SS 304",
        "mat_b": "SS 304",
        "area_a": 0.4,
        "area_b": 0.4,
        "joint": "compression fitting",
        "temp": 15.0,
        "velocity": 0.6,
        "dead_leg": 0.06,
        "x": 8.2,
        "y": 1.1,
        "z": 2.9,
    },
    # High MIC — carbon steel chilled water low flow weathered insulation
    {
        "id": "BG-006",
        "type": "IfcPipeSegment",
        "service": "Chilled Water",
        "floor": "01",
        "zone": "AHU Plant Room",
        "mat_a": "carbon_steel",
        "mat_b": "carbon_steel",
        "area_a": 5.6,
        "area_b": 5.6,
        "joint": "victaulic",
        "temp": 10.0,
        "velocity": 0.08,
        "dead_leg": 0.6,
        "x": 4.5,
        "y": 5.2,
        "z": 3.2,
    },
    # Medium galvanic — carbon steel/brass normal indoor
    {
        "id": "BG-007",
        "type": "IfcPipeFitting",
        "service": "LTHW",
        "floor": "02",
        "zone": "Plantroom",
        "mat_a": "carbon_steel",
        "mat_b": "brass",
        "area_a": 3.2,
        "area_b": 1.1,
        "joint": "socket weld",
        "temp": 80.0,
        "velocity": 0.7,
        "dead_leg": 0.0,
        "x": 6.3,
        "y": 0.8,
        "z": 3.1,
    },
    # Medium crevice — SS316 Victaulic in humid plant room
    {
        "id": "BG-008",
        "type": "IfcPipeSegment",
        "service": "Chilled Water",
        "floor": "B1",
        "zone": "Plant Room",
        "mat_a": "SS 316",
        "mat_b": "SS 316",
        "area_a": 4.8,
        "area_b": 4.8,
        "joint": "victaulic",
        "temp": 12.0,
        "velocity": 0.5,
        "dead_leg": 0.0,
        "x": 1.8,
        "y": 4.6,
        "z": 3.0,
    },
    # Medium MIC — SS316 process unknown temp moderate dead-leg
    {
        "id": "BG-009",
        "type": "IfcPipeSegment",
        "service": "Process Water",
        "floor": "B1",
        "zone": "Process Area",
        "mat_a": "SS 316",
        "mat_b": "SS 316",
        "area_a": 2.9,
        "area_b": 2.9,
        "joint": "butt weld",
        "temp": 25.0,
        "velocity": 0.15,
        "dead_leg": 0.3,
        "x": 9.1,
        "y": 2.8,
        "z": 2.7,
    },
    # Critical — galvanised steel unistrut / SS316 pipe
    {
        "id": "BG-010",
        "type": "IfcPipeSegment",
        "service": "Process Water",
        "floor": "B1",
        "zone": "Plant Room",
        "mat_a": "galv_steel",
        "mat_b": "ss316_passive",
        "area_a": 0.5,
        "area_b": 4.5,
        "joint": "butt weld",
        "temp": 20.0,
        "velocity": 0.9,
        "dead_leg": 0.0,
        "x": 2.9,
        "y": 6.1,
        "z": 3.1,
    },
    # High — domestic hot water dead-leg at 38°C
    {
        "id": "BG-011",
        "type": "IfcPipeSegment",
        "service": "Domestic Hot Water",
        "floor": "03",
        "zone": "Hotel Room",
        "mat_a": "carbon_steel",
        "mat_b": "carbon_steel",
        "area_a": 1.1,
        "area_b": 1.1,
        "joint": "butt weld",
        "temp": 38.0,
        "velocity": 0.05,
        "dead_leg": 0.8,
        "x": 12.4,
        "y": 3.2,
        "z": 9.0,
    },
    # Medium — cast iron pump body / copper
    {
        "id": "BG-012",
        "type": "IfcFlowMovingDevice",
        "service": "LTHW",
        "floor": "B1",
        "zone": "Plant Room",
        "mat_a": "cast_iron",
        "mat_b": "copper",
        "area_a": 2.2,
        "area_b": 2.2,
        "joint": "slip-on flange",
        "temp": 75.0,
        "velocity": 0.6,
        "dead_leg": 0.0,
        "x": 7.3,
        "y": 1.5,
        "z": 3.0,
    },
    # Low — titanium + SS316 pool environment
    {
        "id": "BG-013",
        "type": "IfcPipeSegment",
        "service": "Pool Plant",
        "floor": "B1",
        "zone": "Pool Plant Room",
        "mat_a": "titanium",
        "mat_b": "ss316_passive",
        "area_a": 2.0,
        "area_b": 2.0,
        "joint": "butt weld",
        "temp": 30.0,
        "velocity": 0.8,
        "dead_leg": 0.0,
        "x": 4.1,
        "y": 7.3,
        "z": 2.8,
    },
    # Critical — SS304 flanged pool at 25°C
    {
        "id": "BG-014",
        "type": "IfcPipeFitting",
        "service": "Pool Plant",
        "floor": "B1",
        "zone": "Pool Plant Room",
        "mat_a": "SS 304",
        "mat_b": "SS 304",
        "area_a": 1.8,
        "area_b": 1.8,
        "joint": "weld neck flange",
        "temp": 25.0,
        "velocity": 0.4,
        "dead_leg": 0.0,
        "x": 3.7,
        "y": 8.1,
        "z": 2.8,
    },
    # Low — copper DHW 62°C through-flow
    {
        "id": "BG-015",
        "type": "IfcPipeSegment",
        "service": "Domestic Hot Water",
        "floor": "01",
        "zone": "Kitchen",
        "mat_a": "copper",
        "mat_b": "copper",
        "area_a": 1.5,
        "area_b": 1.5,
        "joint": "butt weld",
        "temp": 62.0,
        "velocity": 0.8,
        "dead_leg": 0.0,
        "x": 15.2,
        "y": 2.1,
        "z": 2.9,
    },
    # High — condenser water warm loop galvanised
    {
        "id": "BG-016",
        "type": "IfcPipeSegment",
        "service": "Condenser Water",
        "floor": "RF",
        "zone": "Cooling Tower",
        "mat_a": "galv_steel",
        "mat_b": "galv_steel",
        "area_a": 6.3,
        "area_b": 6.3,
        "joint": "victaulic",
        "temp": 32.0,
        "velocity": 0.25,
        "dead_leg": 0.0,
        "x": 18.5,
        "y": 1.2,
        "z": 15.0,
    },
    # Medium — SS316 butt weld normal indoor 15°C
    {
        "id": "BG-017",
        "type": "IfcPipeSegment",
        "service": "Domestic Cold Water",
        "floor": "02",
        "zone": "Office",
        "mat_a": "SS 316",
        "mat_b": "SS 316",
        "area_a": 2.1,
        "area_b": 2.1,
        "joint": "butt weld",
        "temp": 15.0,
        "velocity": 0.7,
        "dead_leg": 0.0,
        "x": 9.8,
        "y": 4.5,
        "z": 6.1,
    },
    # Low — CPVC cold water through-flow 12°C
    {
        "id": "BG-018",
        "type": "IfcPipeSegment",
        "service": "Domestic Cold Water",
        "floor": "01",
        "zone": "Office",
        "mat_a": "cpvc",
        "mat_b": "cpvc",
        "area_a": 1.2,
        "area_b": 1.2,
        "joint": "push fit",
        "temp": 12.0,
        "velocity": 1.2,
        "dead_leg": 0.0,
        "x": 11.3,
        "y": 3.6,
        "z": 2.9,
    },
    # Critical — carbon steel domestic cold water dead-leg danger zone
    {
        "id": "BG-019",
        "type": "IfcPipeSegment",
        "service": "Domestic Cold Water",
        "floor": "B2",
        "zone": "Plant Room",
        "mat_a": "carbon_steel",
        "mat_b": "carbon_steel",
        "area_a": 3.4,
        "area_b": 3.4,
        "joint": "socket weld",
        "temp": 28.0,
        "velocity": 0.0,
        "dead_leg": 2.5,
        "x": 6.7,
        "y": 9.2,
        "z": 2.6,
    },
    # Medium — duplex 2205 butt weld coastal external
    {
        "id": "BG-020",
        "type": "IfcPipeSegment",
        "service": "Process Water",
        "floor": "01",
        "zone": "External",
        "mat_a": "duplex 2205",
        "mat_b": "duplex 2205",
        "area_a": 3.8,
        "area_b": 3.8,
        "joint": "butt weld",
        "temp": 20.0,
        "velocity": 0.6,
        "dead_leg": 0.0,
        "x": 22.1,
        "y": 5.4,
        "z": 3.0,
    },
    # High — SS316 threaded joint humid plant room 40°C
    {
        "id": "BG-021",
        "type": "IfcPipeFitting",
        "service": "Domestic Hot Water",
        "floor": "B2",
        "zone": "Plant Room",
        "mat_a": "SS 316",
        "mat_b": "SS 316",
        "area_a": 0.6,
        "area_b": 0.6,
        "joint": "threaded",
        "temp": 40.0,
        "velocity": 0.4,
        "dead_leg": 0.0,
        "x": 5.5,
        "y": 10.2,
        "z": 2.7,
    },
    # Medium — carbon steel / brass valve normal indoor
    {
        "id": "BG-022",
        "type": "IfcValve",
        "service": "LTHW",
        "floor": "03",
        "zone": "Riser",
        "mat_a": "carbon_steel",
        "mat_b": "brass",
        "area_a": 2.8,
        "area_b": 0.9,
        "joint": "socket weld",
        "temp": 75.0,
        "velocity": 0.5,
        "dead_leg": 0.0,
        "x": 14.6,
        "y": 0.4,
        "z": 9.0,
    },
    # Low — duplex 2205 hot water high flow
    {
        "id": "BG-023",
        "type": "IfcPipeSegment",
        "service": "Domestic Hot Water",
        "floor": "RF",
        "zone": "Plant Room",
        "mat_a": "duplex 2205",
        "mat_b": "duplex 2205",
        "area_a": 4.1,
        "area_b": 4.1,
        "joint": "butt weld",
        "temp": 65.0,
        "velocity": 0.7,
        "dead_leg": 0.08,
        "x": 19.3,
        "y": 2.7,
        "z": 15.2,
    },
    # High — aluminium external exposed
    {
        "id": "BG-024",
        "type": "IfcPipeSegment",
        "service": "Drainage",
        "floor": "RF",
        "zone": "Roof",
        "mat_a": "aluminium",
        "mat_b": "carbon_steel",
        "area_a": 5.0,
        "area_b": 1.0,
        "joint": "slip-on flange",
        "temp": 12.0,
        "velocity": 0.3,
        "dead_leg": 0.0,
        "x": 20.8,
        "y": 8.1,
        "z": 15.0,
    },
    # Medium — copper hot water 58°C short dead-leg
    {
        "id": "BG-025",
        "type": "IfcPipeSegment",
        "service": "Domestic Hot Water",
        "floor": "02",
        "zone": "Ward",
        "mat_a": "copper",
        "mat_b": "copper",
        "area_a": 1.4,
        "area_b": 1.4,
        "joint": "compression fitting",
        "temp": 58.0,
        "velocity": 0.45,
        "dead_leg": 0.06,
        "x": 13.1,
        "y": 6.8,
        "z": 6.0,
    },
]


def run_demo_compliance():
    """
    Run all three corrosion engines on the 25 synthetic elements.
    Returns list of result dicts combining GC-001, CC-001, and MC-001.
    """
    if not ENGINES_AVAILABLE:
        return _fallback_results()

    results = []
    for el in DEMO_ELEMENTS:
        row = {
            "id": el["id"],
            "type": el["type"],
            "service": el["service"],
            "floor": el["floor"],
            "zone": el["zone"],
            "mat_a": el["mat_a"],
            "mat_b": el["mat_b"],
            "x": el["x"],
            "y": el["y"],
            "z": el["z"],
        }

        # GC-001
        try:
            gc_el = GCElement(
                global_id_anode=el["id"] + "_A",
                global_id_cathode=el["id"] + "_B",
                material_anode=el["mat_a"],
                material_cathode=el["mat_b"],
                anode_area_m2=el["area_a"],
                cathode_area_m2=el["area_b"],
                zone_category=el["zone"],
                floor=el["floor"],
                system_type=el["service"],
            )
            gc = assess_galvanic_risk(gc_el)
            row["gc_score"] = gc.composite_score
            row["gc_band"] = gc.risk_band
            row["gc_gap"] = gc.voltage_gap_v
            row["gc_env"] = gc.environment_label
        except Exception:
            row["gc_score"] = 0.0
            row["gc_band"] = "Low"
            row["gc_gap"] = 0.0
            row["gc_env"] = "Unknown"

        # CC-001
        try:
            cc_el = CCElement(
                global_id=el["id"],
                element_type=el["type"],
                material=el["mat_a"],
                joint_description=el["joint"],
                operating_temp_c=el["temp"],
                zone_category=el["zone"],
                system_type=el["service"],
                floor=el["floor"],
            )
            cc = assess_crevice_risk(cc_el)
            row["cc_score"] = cc.composite_score
            row["cc_band"] = cc.risk_band
            row["cc_joint"] = cc.joint_type_label
            row["cc_geo"] = cc.geometry_class
        except Exception:
            row["cc_score"] = 0.0
            row["cc_band"] = "Low"
            row["cc_joint"] = "Unknown"
            row["cc_geo"] = "Unknown"

        # MC-001
        try:
            mc_el = MICElement(
                global_id=el["id"],
                element_type=el["type"],
                system_type=el["service"].upper().replace(" ", ""),
                material=el["mat_a"],
                nominal_diameter_m=0.050,
                flow_velocity_ms=el["velocity"],
                operating_temp_c=el["temp"],
                dead_leg_length_m=el["dead_leg"],
                floor=el["floor"],
                zone=el["zone"],
            )
            mc = assess_mic_risk(mc_el)
            row["mc_score"] = mc.composite_score
            row["mc_band"] = mc.risk_band
        except Exception:
            row["mc_score"] = 0.0
            row["mc_band"] = "Low"

        # Combined band = highest of three
        band_rank = {"Low": 0, "Medium": 1, "High": 2, "Critical": 3}
        combined = max(
            row["gc_band"], row["cc_band"], row["mc_band"], key=lambda b: band_rank.get(b, 0)
        )
        row["combined_band"] = combined
        row["combined_score"] = round(max(row["gc_score"], row["cc_score"], row["mc_score"]), 3)

        # Which mechanism drives the combined band
        if row["gc_score"] >= row["cc_score"] and row["gc_score"] >= row["mc_score"]:
            row["primary_mechanism"] = "GC-001 Galvanic"
        elif row["cc_score"] >= row["mc_score"]:
            row["primary_mechanism"] = "CC-001 Crevice"
        else:
            row["primary_mechanism"] = "MC-001 MIC"

        results.append(row)

    return results


def _fallback_results():
    """Hardcoded results for when engines are not importable."""
    bands = [
        "Critical",
        "Critical",
        "Critical",
        "High",
        "High",
        "High",
        "Medium",
        "Medium",
        "Medium",
        "Medium",
        "High",
        "Medium",
        "Low",
        "Critical",
        "Low",
        "High",
        "Medium",
        "Low",
        "Critical",
        "Medium",
        "High",
        "Medium",
        "Low",
        "High",
        "Medium",
    ]
    return [
        {
            "id": el["id"],
            "type": el["type"],
            "service": el["service"],
            "floor": el["floor"],
            "zone": el["zone"],
            "mat_a": el["mat_a"],
            "mat_b": el["mat_b"],
            "gc_score": 0.5,
            "gc_band": bands[i],
            "gc_gap": 0.3,
            "gc_env": "Humid",
            "cc_score": 0.5,
            "cc_band": bands[i],
            "cc_joint": "Flange",
            "cc_geo": "Tight",
            "mc_score": 0.5,
            "mc_band": bands[i],
            "combined_band": bands[i],
            "combined_score": 0.5,
            "primary_mechanism": "GC-001 Galvanic",
            "x": el["x"],
            "y": el["y"],
            "z": el["z"],
        }
        for i, el in enumerate(DEMO_ELEMENTS)
    ]


def get_summary(results):
    """Return summary statistics dict from a results list."""
    bands = {"Critical": 0, "High": 0, "Medium": 0, "Low": 0}
    for r in results:
        b = r.get("combined_band", "Low")
        bands[b] = bands.get(b, 0) + 1
    issues = sum(v for k, v in bands.items() if k != "Low")
    total_cost = sum(
        {"Critical": 8800, "High": 5000, "Medium": 2200, "Low": 0}.get(r["combined_band"], 0)
        for r in results
    )
    return {
        "total": len(results),
        "issues": issues,
        "bands": bands,
        "cost": total_cost,
        "cost_avoidance": total_cost * 5,
    }
