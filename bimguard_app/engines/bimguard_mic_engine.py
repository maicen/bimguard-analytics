"""
BIMGUARD AI — Microbially Influenced Corrosion Engine
Ruleset: BIMGUARD-MC-001 v1.0.0

Standards referenced:
  - CIBSE TM13:2013 (Minimising the Risk of Legionella)
  - HSE HSG274 Parts 1–3 (Legionella Control)
  - BS 8552:2012 (Sampling and Monitoring of Water)
  - ASTM G-187 (MIC Assessment)
  - EN ISO 9308-1 (Microbiological Water Quality)
  - CIBSE Guide G (Public Health Engineering)
  - WHO Guidelines for Drinking Water Quality (4th Ed.)
  - NACCE TPC 11 (MIC in Industrial Water Systems)

Weighted composite score:
  Score_MC = (0.35 × flow_velocity_risk)
            + (0.30 × temperature_risk)
            + (0.25 × dead_leg_risk)
            + (0.10 × material_susceptibility)

Risk bands:
  Low      < 0.25
  Medium   0.25 – 0.50
  High     0.50 – 0.75
  Critical > 0.75
"""

import csv
import os
import uuid
import zipfile
from dataclasses import dataclass
from datetime import datetime
from typing import Optional

# ── VERSION ───────────────────────────────────────────────────────────────────
RULESET_VERSION = "BIMGUARD-MC-001 v1.0.0"
ASSESSMENT_DATE = datetime.utcnow().isoformat() + "Z"

# ── FLOW VELOCITY CLASSES ─────────────────────────────────────────────────────
# Based on CIBSE TM13:2013 and HSE HSG274
# Stagnation is the primary enabler of biofilm formation
FLOW_VELOCITY_CLASSES = {
    "FV0_STAGNANT": {
        "label": "Stagnant / dead-leg",
        "threshold_ms": 0.0,
        "risk": 1.00,
        "mic_risk": "Critical — biofilm establishment certain",
    },
    "FV1_VERY_LOW": {
        "label": "Very low flow < 0.1 m/s",
        "threshold_ms": 0.1,
        "risk": 0.80,
        "mic_risk": "High — insufficient flushing velocity",
    },
    "FV2_LOW": {
        "label": "Low flow 0.1–0.3 m/s",
        "threshold_ms": 0.3,
        "risk": 0.55,
        "mic_risk": "Moderate — marginal flushing",
    },
    "FV3_ACCEPTABLE": {
        "label": "Acceptable 0.3–0.6 m/s",
        "threshold_ms": 0.6,
        "risk": 0.25,
        "mic_risk": "Low — adequate flushing for most services",
    },
    "FV4_GOOD": {
        "label": "Good flow 0.6–1.5 m/s",
        "threshold_ms": 1.5,
        "risk": 0.10,
        "mic_risk": "Very low — self-cleaning velocity",
    },
    "FV5_TURBULENT": {
        "label": "Turbulent > 1.5 m/s",
        "threshold_ms": 999,
        "risk": 0.02,
        "mic_risk": "Negligible — turbulent regime inhibits biofilm",
    },
}


def classify_flow_velocity(velocity_ms: float) -> tuple[str, dict]:
    """Classify flow velocity and return risk class and metadata."""
    if velocity_ms <= 0.0:
        return "FV0_STAGNANT", FLOW_VELOCITY_CLASSES["FV0_STAGNANT"]
    elif velocity_ms < 0.1:
        return "FV1_VERY_LOW", FLOW_VELOCITY_CLASSES["FV1_VERY_LOW"]
    elif velocity_ms < 0.3:
        return "FV2_LOW", FLOW_VELOCITY_CLASSES["FV2_LOW"]
    elif velocity_ms < 0.6:
        return "FV3_ACCEPTABLE", FLOW_VELOCITY_CLASSES["FV3_ACCEPTABLE"]
    elif velocity_ms <= 1.5:
        return "FV4_GOOD", FLOW_VELOCITY_CLASSES["FV4_GOOD"]
    else:
        return "FV5_TURBULENT", FLOW_VELOCITY_CLASSES["FV5_TURBULENT"]


# ── TEMPERATURE CLASSES ───────────────────────────────────────────────────────
# Based on WHO Guidelines and CIBSE TM13:2013
# Legionella pneumophila growth optimum: 35–46°C
# SRB optimum: 25–35°C (mesophilic), some to 65°C (thermophilic)
# APB range: 15–45°C
TEMPERATURE_CLASSES = {
    "T0_COLD": {
        "range": "<20°C",
        "t_min": 0,
        "t_max": 20,
        "risk": 0.15,
        "organisms": "SRB low activity, minimal Legionella risk (WHO cold water <20°C)",
    },
    "T1_MARGINAL": {
        "range": "20–25°C",
        "t_min": 20,
        "t_max": 25,
        "risk": 0.35,
        "organisms": "SRB active, Legionella survival zone begins",
    },
    "T2_DANGER": {
        "range": "25–45°C",
        "t_min": 25,
        "t_max": 45,
        "risk": 1.00,
        "organisms": "CRITICAL — Legionella proliferation zone. SRB + APB optimal. CIBSE TM13 danger zone",
    },
    "T3_TOLERABLE": {
        "range": "45–55°C",
        "t_min": 45,
        "t_max": 55,
        "risk": 0.45,
        "organisms": "Legionella above optimum but survives to 55°C. Thermophilic SRB active",
    },
    "T4_SAFE_HOT": {
        "range": ">55°C",
        "t_min": 55,
        "t_max": 999,
        "risk": 0.05,
        "organisms": "Legionella destroyed above 60°C (CIBSE TM13). SRB inhibited",
    },
    "T5_UNKNOWN": {
        "range": "Unknown",
        "t_min": -1,
        "t_max": -1,
        "risk": 0.65,
        "organisms": "Temperature unknown — conservative risk applied (default ambient 20°C applied)",
    },
}


def classify_temperature(temp_c: Optional[float]) -> tuple[str, dict]:
    """Classify operating temperature and return risk class."""
    if temp_c is None:
        return "T5_UNKNOWN", TEMPERATURE_CLASSES["T5_UNKNOWN"]
    for key, data in TEMPERATURE_CLASSES.items():
        if key == "T5_UNKNOWN":
            continue
        if data["t_min"] <= temp_c < data["t_max"]:
            return key, data
    return "T4_SAFE_HOT", TEMPERATURE_CLASSES["T4_SAFE_HOT"]


# ── DEAD-LEG CLASSIFICATION ───────────────────────────────────────────────────
# Based on HSE HSG274 Part 2 and CIBSE Guide G
# Dead-leg length ratio = dead-leg length / supply pipe diameter
# A dead-leg length > 3× diameter is the standard HSE threshold
DEAD_LEG_CLASSES = {
    "DL0_THROUGH": {
        "label": "Through-flow (no dead-leg)",
        "risk": 0.05,
        "ratio_threshold": 0,
        "description": "Active flow path — no stagnation geometry",
    },
    "DL1_SHORT": {
        "label": "Short dead-leg (< 3D)",
        "risk": 0.30,
        "ratio_threshold": 3,
        "description": "Below HSE HSG274 threshold — low stagnation risk",
    },
    "DL2_MODERATE": {
        "label": "Moderate dead-leg (3D – 10D)",
        "risk": 0.65,
        "ratio_threshold": 10,
        "description": "Exceeds HSE threshold — flushing regime required",
    },
    "DL3_LONG": {
        "label": "Long dead-leg (10D – 20D)",
        "risk": 0.85,
        "ratio_threshold": 20,
        "description": "High stagnation — consider elimination or auto-flush",
    },
    "DL4_CRITICAL": {
        "label": "Critical dead-leg (> 20D)",
        "risk": 1.00,
        "ratio_threshold": 999,
        "description": "Critical stagnation geometry — eliminate or install auto-flush",
    },
    "DL5_UNKNOWN": {
        "label": "Dead-leg unknown",
        "risk": 0.50,
        "ratio_threshold": -1,
        "description": "Topology not determinable from IFC — conservative default",
    },
}


def classify_dead_leg(length_m: Optional[float], diameter_m: Optional[float]) -> tuple[str, dict]:
    """
    Classify dead-leg by length-to-diameter ratio per HSE HSG274.
    Returns risk class key and metadata dict.
    """
    if length_m is None or diameter_m is None or diameter_m == 0:
        return "DL5_UNKNOWN", DEAD_LEG_CLASSES["DL5_UNKNOWN"]
    if length_m <= 0:
        return "DL0_THROUGH", DEAD_LEG_CLASSES["DL0_THROUGH"]
    ratio = length_m / diameter_m
    if ratio < 3:
        return "DL1_SHORT", DEAD_LEG_CLASSES["DL1_SHORT"]
    elif ratio < 10:
        return "DL2_MODERATE", DEAD_LEG_CLASSES["DL2_MODERATE"]
    elif ratio < 20:
        return "DL3_LONG", DEAD_LEG_CLASSES["DL3_LONG"]
    else:
        return "DL4_CRITICAL", DEAD_LEG_CLASSES["DL4_CRITICAL"]


# ── MATERIAL SUSCEPTIBILITY ───────────────────────────────────────────────────
# Based on ASTM G-187 and NACCE TPC 11
# MIC susceptibility differs from galvanic/crevice — copper and some alloys
# have antimicrobial properties; carbon steel and cast iron are highly susceptible
MATERIAL_SUSCEPTIBILITY = {
    # key: (susceptibility_score, label, notes)
    "carbon_steel": (
        1.00,
        "Carbon / mild steel",
        "Highly susceptible — iron provides nutrient for IOB and SRB. Pitting under biofilm common",
    ),
    "cast_iron": (
        0.90,
        "Cast iron",
        "High susceptibility — large surface area, graphitic corrosion under biofilm",
    ),
    "galv_steel": (
        0.75,
        "Galvanised steel",
        "Moderate-high — zinc coating inhibits initially but SRB attack underlying steel when depleted",
    ),
    "ss304": (
        0.30,
        "Stainless steel 304",
        "Low susceptibility — passive film resists MIC. Risk increases under biofilm in stagnant conditions",
    ),
    "ss316": (
        0.20,
        "Stainless steel 316",
        "Low — Mo addition improves resistance. Still at risk from SRB pitting in anaerobic stagnant zones",
    ),
    "duplex2205": (
        0.10,
        "Duplex 2205",
        "Very low — high Cr+Mo content provides strong MIC resistance",
    ),
    "copper": (
        0.15,
        "Copper",
        "Low — antimicrobial properties inhibit biofilm. Risk from APB in acidic conditions (dezincification)",
    ),
    "brass": (
        0.25,
        "Brass (70/30)",
        "Low-moderate — antimicrobial but susceptible to dealloying under biofilm",
    ),
    "bronze": (0.20, "Bronze", "Low — similar to copper; antimicrobial properties effective"),
    "cpvc": (
        0.05,
        "CPVC",
        "Negligible — non-metallic; biofilm substrate only, no metallic corrosion",
    ),
    "pvc": (0.05, "PVC", "Negligible — non-metallic; biofilm can form but no MIC of pipe material"),
    "hdpe": (0.05, "HDPE", "Negligible — non-metallic; inert to MIC"),
    "titanium": (
        0.05,
        "Titanium",
        "Negligible — exceptional MIC resistance; used in aggressive MIC environments",
    ),
    "aluminium": (
        0.50,
        "Aluminium",
        "Moderate — susceptible to pitting under biofilm, particularly in chloride environments",
    ),
    "unknown": (
        0.60,
        "Unknown material",
        "Conservative default — material not identified in IFC model",
    ),
}


def get_material_susceptibility(material_key: str) -> tuple[float, str, str]:
    """Return (score, label, notes) for a material key."""
    key = material_key.lower().replace(" ", "_").replace("-", "_")
    # Normalise common variants
    aliases = {
        "carbon steel": "carbon_steel",
        "mild steel": "carbon_steel",
        "cs": "carbon_steel",
        "ms": "carbon_steel",
        "galvanised": "galv_steel",
        "galvanized": "galv_steel",
        "ss 304": "ss304",
        "304": "ss304",
        "1.4301": "ss304",
        "ss 316": "ss316",
        "316": "ss316",
        "316l": "ss316",
        "1.4401": "ss316",
        "2205": "duplex2205",
        "duplex": "duplex2205",
        "cu": "copper",
        "copper tube": "copper",
    }
    resolved = aliases.get(key, key)
    return MATERIAL_SUSCEPTIBILITY.get(resolved, MATERIAL_SUSCEPTIBILITY["unknown"])


# ── UNDER-INSULATION CORROSION (UIC) ─────────────────────────────────────────
# Based on NACE SP0198 and CIBSE Guide G
# Under-insulation creates trapped moisture, restricted oxygen, and warm
# temperatures that are ideal for SRB and APB colonisation
UNDER_INSULATION_RISK = {
    "none": 0.00,  # No insulation
    "good_condition": 0.10,  # Insulation present, intact, no moisture ingress
    "weathered": 0.45,  # Insulation weathered/aged — moisture ingress possible
    "damaged": 0.80,  # Insulation visibly damaged — moisture trapped
    "wet": 1.00,  # Wet insulation confirmed — MIC very likely
    "unknown": 0.35,  # Insulation present but condition unknown
}

# ── SYSTEM TYPE RISK MODIFIER ─────────────────────────────────────────────────
# Certain system types have inherent MIC risk regardless of individual element conditions
SYSTEM_TYPE_MODIFIERS = {
    # IfcDistributionSystem types → (multiplier, description)
    "DOMESTICCOLDWATER": (1.30, "Domestic cold water — primary Legionella risk system"),
    "DOMESTICHOTWATER": (1.25, "Domestic hot water — Legionella proliferation if < 55°C"),
    "CHILLEDWATER": (1.15, "Chilled water — temperature 7–12°C favours biofilm in low-flow zones"),
    "CONDENSERWATER": (1.20, "Condenser water — warm recirculating system, high MIC risk"),
    "FIREPROTECTION": (1.40, "Fire suppression — infrequent flow, long stagnation periods"),
    "IRRIGATION": (1.10, "Irrigation — intermittent flow, warm conditions"),
    "WASTEWATER": (0.80, "Waste / drain — anaerobic SRB active but corrosion consequence lower"),
    "PROCESSWATER": (1.00, "Process water — risk depends on operating conditions"),
    "UNKNOWN": (1.05, "Unknown system type — slight conservative uplift"),
}


def get_system_modifier(system_type: str) -> tuple[float, str]:
    """Return (multiplier, description) for a system type string."""
    for key, val in SYSTEM_TYPE_MODIFIERS.items():
        if key in system_type.upper():
            return val
    return SYSTEM_TYPE_MODIFIERS["UNKNOWN"]


# ── RISK BAND CLASSIFICATION ──────────────────────────────────────────────────
def classify_mic_risk(score: float) -> tuple[str, str]:
    """
    Map composite score to risk band.
    Returns (band_label, bcf_priority).
    """
    if score < 0.25:
        return "Low", "Minor"
    elif score < 0.50:
        return "Medium", "Normal"
    elif score < 0.75:
        return "High", "Major"
    else:
        return "Critical", "Critical"


# ── MITIGATION CATALOGUE ──────────────────────────────────────────────────────
MITIGATIONS = {
    "MIT-MIC-001": "Eliminate dead-leg — reconfigure pipework to active through-flow configuration (HSE HSG274 preferred solution)",
    "MIT-MIC-002": "Install automatic flushing device — programme to flush weekly at minimum (CIBSE TM13 requirement)",
    "MIT-MIC-003": "Increase design flow velocity to minimum 0.3 m/s — revise pipe sizing or reroute to reduce network length",
    "MIT-MIC-004": "Raise hot water storage and distribution temperature to minimum 60°C storage / 55°C at outlets (HSE HSG274 Part 2)",
    "MIT-MIC-005": "Reduce cold water temperature to below 20°C — review insulation against heat gain from adjacent services",
    "MIT-MIC-006": "Specify copper or CPVC pipework in replacement — antimicrobial material substitution",
    "MIT-MIC-007": "Repair or replace damaged/wet insulation — prevent under-insulation moisture accumulation",
    "MIT-MIC-008": "Implement biocide dosing programme — chlorination or alternative biocide per BS 8552",
    "MIT-MIC-009": "Introduce microbiological monitoring programme — EN ISO 9308-1 sampling at identified risk points",
    "MIT-MIC-010": "Conduct thermal disinfection — pasteurisation at minimum 70°C for 1 hour (CIBSE TM13 emergency response)",
}


def select_mitigation(
    flow_class: str, temp_class: str, dead_leg_class: str, material_key: str
) -> list[str]:
    """Select appropriate mitigations based on primary risk drivers."""
    mits = []
    if dead_leg_class in ("DL4_CRITICAL", "DL3_LONG"):
        mits.append("MIT-MIC-001")
    if dead_leg_class in ("DL2_MODERATE", "DL1_SHORT"):
        mits.append("MIT-MIC-002")
    if flow_class in ("FV0_STAGNANT", "FV1_VERY_LOW", "FV2_LOW"):
        mits.append("MIT-MIC-003")
    if temp_class == "T2_DANGER":
        mits.append("MIT-MIC-004")
        mits.append("MIT-MIC-005")
    if material_key in ("carbon_steel", "cast_iron", "galv_steel"):
        mits.append("MIT-MIC-006")
    mits.append("MIT-MIC-009")
    return list(dict.fromkeys(mits))  # deduplicate preserving order


# ── MAIN ASSESSMENT DATACLASS ─────────────────────────────────────────────────
@dataclass
class MICElement:
    """Input data for a single piping element to be assessed by MC-001."""

    global_id: str
    element_type: str  # e.g. "IfcPipeSegment"
    system_type: str  # e.g. "DOMESTICCOLDWATER"
    material: str  # material name string from IFC
    nominal_diameter_m: float  # pipe OD in metres
    flow_velocity_ms: Optional[float] = None
    operating_temp_c: Optional[float] = None
    dead_leg_length_m: Optional[float] = None
    insulation_condition: str = "unknown"
    floor: str = "Unknown"
    zone: str = "Unknown"
    # Calculated fields
    position_x: float = 0.0
    position_y: float = 0.0
    position_z: float = 0.0


@dataclass
class MICResult:
    """Full MC-001 assessment result for one element."""

    global_id: str
    element_type: str
    system_type: str
    material_label: str
    material_key: str
    floor: str
    zone: str
    # Sub-scores
    flow_velocity_class: str
    flow_velocity_risk: float
    temperature_class: str
    temperature_risk: float
    dead_leg_class: str
    dead_leg_risk: float
    material_susceptibility_score: float
    system_modifier: float
    under_insulation_risk: float
    # Composite
    composite_score: float
    risk_band: str
    bcf_priority: str
    mitigations: list[str]
    # Metadata
    ruleset_version: str = RULESET_VERSION
    assessment_date: str = ASSESSMENT_DATE


# ── CORE ASSESSMENT FUNCTION ──────────────────────────────────────────────────
def assess_mic_risk(element: MICElement) -> MICResult:
    """
    Run MC-001 MIC risk assessment on a single piping element.

    Weighted composite score:
    Score_MC = (0.35 × flow_velocity_risk)
              + (0.30 × temperature_risk)
              + (0.25 × dead_leg_risk)
              + (0.10 × material_susceptibility)

    Score is then modified by system_type multiplier and capped at 1.00.
    Under-insulation risk is added as an independent pathway — if UIC risk
    exceeds the base MIC score, it is used instead (worst-case of the two paths).
    """
    # Flow velocity
    fv_class, fv_data = classify_flow_velocity(
        element.flow_velocity_ms if element.flow_velocity_ms is not None else 0.0
    )
    fv_risk = fv_data["risk"]

    # Temperature
    t_class, t_data = classify_temperature(element.operating_temp_c)
    t_risk = t_data["risk"]

    # Dead-leg
    dl_class, dl_data = classify_dead_leg(element.dead_leg_length_m, element.nominal_diameter_m)
    dl_risk = dl_data["risk"]

    # Material susceptibility
    mat_score, mat_label, _ = get_material_susceptibility(element.material)

    # System modifier
    sys_mult, _ = get_system_modifier(element.system_type)

    # Under-insulation risk (independent pathway)
    uic_risk = UNDER_INSULATION_RISK.get(
        element.insulation_condition.lower(), UNDER_INSULATION_RISK["unknown"]
    )

    # Base composite score
    base_score = 0.35 * fv_risk + 0.30 * t_risk + 0.25 * dl_risk + 0.10 * mat_score

    # Apply system modifier
    modified_score = base_score * sys_mult

    # Under-insulation is an independent pathway — take worst case
    composite_score = min(1.00, max(modified_score, uic_risk * 0.85))

    risk_band, bcf_priority = classify_mic_risk(composite_score)
    mitigations = select_mitigation(fv_class, t_class, dl_class, element.material)

    return MICResult(
        global_id=element.global_id,
        element_type=element.element_type,
        system_type=element.system_type,
        material_label=mat_label,
        material_key=element.material,
        floor=element.floor,
        zone=element.zone,
        flow_velocity_class=fv_class,
        flow_velocity_risk=round(fv_risk, 3),
        temperature_class=t_class,
        temperature_risk=round(t_risk, 3),
        dead_leg_class=dl_class,
        dead_leg_risk=round(dl_risk, 3),
        material_susceptibility_score=round(mat_score, 3),
        system_modifier=round(sys_mult, 3),
        under_insulation_risk=round(uic_risk, 3),
        composite_score=round(composite_score, 3),
        risk_band=risk_band,
        bcf_priority=bcf_priority,
        mitigations=mitigations,
    )


def assess_mic_batch(elements: list[MICElement]) -> list[MICResult]:
    """Run MC-001 on a list of elements and return all results."""
    return [assess_mic_risk(el) for el in elements]


# ── BCF 2.1 EXPORT ────────────────────────────────────────────────────────────
def generate_mic_bcf(results: list[MICResult], output_path: str) -> int:
    """
    Generate BCF 2.1 compliant ZIP archive for MC-001 findings.
    Only Medium, High, and Critical results generate BCF issues.
    Returns count of issues generated.
    """
    issues = [r for r in results if r.risk_band != "Low"]
    if not issues:
        return 0

    with zipfile.ZipFile(output_path, "w", zipfile.ZIP_DEFLATED) as zf:
        for result in issues:
            issue_id = str(uuid.uuid4())
            mit_text = "\n".join(f"  {k}: {MITIGATIONS.get(k, k)}" for k in result.mitigations)
            markup = f"""<?xml version="1.0" encoding="utf-8"?>
<Markup xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance">
  <Topic Guid="{issue_id}" TopicType="Issue" TopicStatus="Open">
    <Title>MC-001 MIC Risk — {result.risk_band} — {result.element_type} [{result.global_id[:8]}]</Title>
    <Priority>{result.bcf_priority}</Priority>
    <CreationDate>{result.assessment_date}</CreationDate>
    <CreationAuthor>BIMGUARD AI — MC-001 v1.0.0</CreationAuthor>
    <AssignedTo>Mechanical / Public Health Engineer</AssignedTo>
    <Description>
Microbially Influenced Corrosion (MIC) Risk Assessment — {RULESET_VERSION}

Element: {result.element_type}
GlobalID: {result.global_id}
System: {result.system_type}
Material: {result.material_label}
Floor: {result.floor}  |  Zone: {result.zone}

COMPOSITE SCORE: {result.composite_score:.3f}  |  RISK BAND: {result.risk_band}

Sub-scores:
  Flow velocity class: {result.flow_velocity_class}  (risk: {result.flow_velocity_risk:.3f})
  Temperature class: {result.temperature_class}  (risk: {result.temperature_risk:.3f})
  Dead-leg class: {result.dead_leg_class}  (risk: {result.dead_leg_risk:.3f})
  Material susceptibility: {result.material_susceptibility_score:.3f}
  System type modifier: {result.system_modifier:.3f}×
  Under-insulation risk: {result.under_insulation_risk:.3f}

Scoring formula (MC-001 v1.0.0):
  Score = (0.35 × {result.flow_velocity_risk:.3f}) + (0.30 × {result.temperature_risk:.3f})
         + (0.25 × {result.dead_leg_risk:.3f}) + (0.10 × {result.material_susceptibility_score:.3f})
         × {result.system_modifier:.3f} [system modifier]
  = {result.composite_score:.3f}

Recommended mitigations:
{mit_text}

Relevant standards:
  CIBSE TM13:2013 — Minimising Risk from Legionella
  HSE HSG274 Parts 1–3 — Legionella Control
  BS 8552:2012 — Sampling and Monitoring of Water Systems
  ASTM G-187 — MIC Assessment Standard Practice
    </Description>
    <Components>
      <Component IfcGuid="{result.global_id}" Selected="true" Visible="true"/>
    </Components>
  </Topic>
</Markup>"""
            viewpoint = f"""<?xml version="1.0" encoding="utf-8"?>
<VisualizationInfo Guid="{issue_id}">
  <Components>
    <Selection>
      <Component IfcGuid="{result.global_id}"/>
    </Selection>
  </Components>
  <PerspectiveCamera>
    <CameraViewPoint><X>0</X><Y>0</Y><Z>5</Z></CameraViewPoint>
    <CameraDirection><X>0</X><Y>1</Y><Z>-0.5</Z></CameraDirection>
    <CameraUpVector><X>0</X><Y>0</Y><Z>1</Z></CameraUpVector>
    <FieldOfView>60</FieldOfView>
  </PerspectiveCamera>
</VisualizationInfo>"""
            zf.writestr(f"{issue_id}/markup.bcf", markup)
            zf.writestr(f"{issue_id}/viewpoint.bcfv", viewpoint)

    return len(issues)


# ── ASSET REGISTER EXPORT ─────────────────────────────────────────────────────
def export_mic_asset_register(results: list[MICResult], output_path: str) -> None:
    """Export MC-001 results to CSV asset register."""
    fieldnames = [
        "GlobalID",
        "ElementType",
        "SystemType",
        "MaterialLabel",
        "Floor",
        "Zone",
        "FlowVelocityClass",
        "FlowVelocityRisk",
        "TemperatureClass",
        "TemperatureRisk",
        "DeadLegClass",
        "DeadLegRisk",
        "MaterialSusceptibility",
        "SystemModifier",
        "UnderInsulationRisk",
        "CompositeScore",
        "RiskBand",
        "BCFPriority",
        "Mitigations",
        "RulesetVersion",
        "AssessmentDate",
    ]
    with open(output_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for r in results:
            writer.writerow(
                {
                    "GlobalID": r.global_id,
                    "ElementType": r.element_type,
                    "SystemType": r.system_type,
                    "MaterialLabel": r.material_label,
                    "Floor": r.floor,
                    "Zone": r.zone,
                    "FlowVelocityClass": r.flow_velocity_class,
                    "FlowVelocityRisk": r.flow_velocity_risk,
                    "TemperatureClass": r.temperature_class,
                    "TemperatureRisk": r.temperature_risk,
                    "DeadLegClass": r.dead_leg_class,
                    "DeadLegRisk": r.dead_leg_risk,
                    "MaterialSusceptibility": r.material_susceptibility_score,
                    "SystemModifier": r.system_modifier,
                    "UnderInsulationRisk": r.under_insulation_risk,
                    "CompositeScore": r.composite_score,
                    "RiskBand": r.risk_band,
                    "BCFPriority": r.bcf_priority,
                    "Mitigations": " | ".join(r.mitigations),
                    "RulesetVersion": r.ruleset_version,
                    "AssessmentDate": r.assessment_date,
                }
            )


# ── CLI VALIDATION DEMO ───────────────────────────────────────────────────────
def run_validation_demo():
    """
    10 validation scenarios demonstrating the MC-001 engine.
    Scenarios cover the range of expected real-world MIC conditions.
    """
    print("=" * 72)
    print("BIMGUARD AI — MC-001 MIC Validation Suite")
    print(f"Ruleset: {RULESET_VERSION}")
    print(f"Date: {ASSESSMENT_DATE}")
    print("=" * 72)

    scenarios = [
        # --- CRITICAL risk scenarios ---
        MICElement(
            global_id="MIC-VAL-001",
            element_type="IfcPipeSegment",
            system_type="DOMESTICCOLDWATER",
            material="carbon_steel",
            nominal_diameter_m=0.050,
            flow_velocity_ms=0.0,  # Stagnant dead-leg
            operating_temp_c=28.0,  # Danger zone
            dead_leg_length_m=2.5,  # 2500mm / 50mm = 50D ratio → Critical
            insulation_condition="none",
            floor="B1",
            zone="Plant Room",
        ),
        MICElement(
            global_id="MIC-VAL-002",
            element_type="IfcPipeSegment",
            system_type="FIREPROTECTION",
            material="carbon_steel",
            nominal_diameter_m=0.080,
            flow_velocity_ms=0.0,  # Fire suppression — never flows
            operating_temp_c=22.0,  # Above 20°C ambient
            dead_leg_length_m=8.0,  # 8000mm / 80mm = 100D → Critical
            insulation_condition="none",
            floor="B2",
            zone="Car Park",
        ),
        MICElement(
            global_id="MIC-VAL-003",
            element_type="IfcPipeSegment",
            system_type="DOMESTICHOTWATER",
            material="carbon_steel",
            nominal_diameter_m=0.022,
            flow_velocity_ms=0.05,  # Near-stagnant
            operating_temp_c=38.0,  # Perfect Legionella temperature
            dead_leg_length_m=0.8,  # 800mm / 22mm = 36D → Critical
            insulation_condition="unknown",
            floor="03",
            zone="Hotel Room",
        ),
        # --- HIGH risk scenarios ---
        MICElement(
            global_id="MIC-VAL-004",
            element_type="IfcPipeSegment",
            system_type="CHILLEDWATER",
            material="carbon_steel",
            nominal_diameter_m=0.100,
            flow_velocity_ms=0.08,  # Very low — near stagnant
            operating_temp_c=10.0,  # Cold — below Legionella but biofilm active
            dead_leg_length_m=0.6,  # 600mm / 100mm = 6D → Moderate
            insulation_condition="weathered",
            floor="01",
            zone="AHU Plantroom",
        ),
        MICElement(
            global_id="MIC-VAL-005",
            element_type="IfcPipeSegment",
            system_type="CONDENSERWATER",
            material="galv_steel",
            nominal_diameter_m=0.150,
            flow_velocity_ms=0.25,  # Low flow
            operating_temp_c=32.0,  # Condenser return — warm
            dead_leg_length_m=None,  # Unknown topology
            insulation_condition="none",
            floor="RF",
            zone="Cooling Tower",
        ),
        # --- MEDIUM risk scenarios ---
        MICElement(
            global_id="MIC-VAL-006",
            element_type="IfcPipeSegment",
            system_type="DOMESTICHOTWATER",
            material="copper",
            nominal_diameter_m=0.028,
            flow_velocity_ms=0.45,  # Acceptable but marginal
            operating_temp_c=58.0,  # Good hot water temperature
            dead_leg_length_m=0.06,  # 60mm / 28mm = 2.1D → Short
            insulation_condition="good_condition",
            floor="02",
            zone="Ward",
        ),
        MICElement(
            global_id="MIC-VAL-007",
            element_type="IfcPipeSegment",
            system_type="PROCESSWATER",
            material="ss316",
            nominal_diameter_m=0.050,
            flow_velocity_ms=0.15,  # Low but not stagnant
            operating_temp_c=None,  # Temperature unknown
            dead_leg_length_m=0.3,  # 300mm / 50mm = 6D → Moderate
            insulation_condition="unknown",
            floor="B1",
            zone="Process Area",
        ),
        # --- LOW risk scenarios ---
        MICElement(
            global_id="MIC-VAL-008",
            element_type="IfcPipeSegment",
            system_type="DOMESTICHOTWATER",
            material="copper",
            nominal_diameter_m=0.022,
            flow_velocity_ms=0.8,  # Good velocity
            operating_temp_c=62.0,  # Above 60°C — Legionella killed
            dead_leg_length_m=0.0,  # Through-flow — no dead-leg
            insulation_condition="good_condition",
            floor="01",
            zone="Kitchen",
        ),
        MICElement(
            global_id="MIC-VAL-009",
            element_type="IfcPipeSegment",
            system_type="DOMESTICCOLDWATER",
            material="cpvc",
            nominal_diameter_m=0.032,
            flow_velocity_ms=1.2,  # Good velocity
            operating_temp_c=12.0,  # Cold and well below 20°C
            dead_leg_length_m=0.0,  # Through-flow
            insulation_condition="good_condition",
            floor="01",
            zone="Office",
        ),
        MICElement(
            global_id="MIC-VAL-010",
            element_type="IfcPipeSegment",
            system_type="DOMESTICHOTWATER",
            material="duplex2205",
            nominal_diameter_m=0.080,
            flow_velocity_ms=0.7,  # Good velocity
            operating_temp_c=65.0,  # High temp
            dead_leg_length_m=0.08,  # 80mm / 80mm = 1D → Short
            insulation_condition="good_condition",
            floor="RF",
            zone="Plant Room",
        ),
    ]

    results = []
    print(f"\n{'ID':<15} {'System':<20} {'Material':<18} {'Score':>7} {'Band':<10} {'Description'}")
    print("-" * 105)
    for sc in scenarios:
        r = assess_mic_risk(sc)
        results.append(r)
        print(
            f"{sc.global_id:<15} {sc.system_type:<20} {r.material_label:<18} {r.composite_score:>7.3f}  {r.risk_band:<10}  "
        )

    print("\n" + "=" * 72)

    # Summary
    bands = {"Low": 0, "Medium": 0, "High": 0, "Critical": 0}
    for r in results:
        bands[r.risk_band] += 1

    print(f"\nSummary: {len(results)} elements assessed")
    for band, count in bands.items():
        if count:
            print(f"  {band}: {count}")

    # Export outputs
    os.makedirs("output", exist_ok=True)
    bcf_path = "output/bimguard_mc001_validation.bcf.zip"
    csv_path = "output/bimguard_mc001_asset_register.csv"

    issues = generate_mic_bcf(results, bcf_path)
    export_mic_asset_register(results, csv_path)

    print(f"\nBCF issues generated: {issues} → {bcf_path}")
    print(f"Asset register exported → {csv_path}")
    print(f"\nRuleset: {RULESET_VERSION}")
    print("=" * 72)

    return results


if __name__ == "__main__":
    run_validation_demo()
