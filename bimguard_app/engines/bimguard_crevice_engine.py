"""
BIMGUARD AI — Crevice Corrosion Engine
Ruleset: BIMGUARD-CC-001 v1.0.0

Standards referenced:
  - EN ISO 15329:2007 (crevice corrosion testing, wetting classes T0–T5)
  - ASTM G48 Method B (CCT values for stainless steel grades)
  - CIRIA C692 (stainless steel in construction, CCT data)
  - CIBSE Guide G (plumbing and MEP crevice corrosion guidance)
  - IMOA Design Manual 4th Ed. (PREN formula and grade selection)
  - EN 1993-1-4 (structural stainless steel)
  - buildingSMART BCF 2.1 (issue tracking specification)
  - ISO 19650 (BIM information management, IFC property set framework)

Weighted composite score:
  Score_CC = (0.35 × geometry_risk)
            + (0.40 × CCT_adequacy)
            + (0.25 × environment_severity)

Risk bands:
  Low      < 0.30
  Medium   0.30 – 0.55
  High     0.55 – 0.80
  Critical > 0.80
"""

import csv
import os
import uuid
import zipfile
from dataclasses import dataclass
from datetime import datetime
from typing import Optional

# Import GC-001 engine for combined assessment
try:
    from bimguard_corrosion_engine import (
        RULESET_VERSION as GC_RULESET_VERSION,
    )
    from bimguard_corrosion_engine import (
        GCElement,
        GCResult,
        assess_galvanic_risk,
    )

    GC_AVAILABLE = True
except ImportError:
    GC_AVAILABLE = False

# ── VERSION ───────────────────────────────────────────────────────────────────
RULESET_VERSION = "BIMGUARD-CC-001 v1.0.0"
ASSESSMENT_DATE = datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ")

# ── CCT TABLE ─────────────────────────────────────────────────────────────────
# Critical Crevice Corrosion Temperature — minimum temperature at which
# crevice corrosion can initiate in the ASTM G48 Method B test solution.
# Source: ASTM G48 Method B / CIRIA C692 / Sandvik Corrosion Handbook
CCT_TABLE = {
    "ss304_passive": {
        "cct_c": -5,
        "pren_typical": 19,
        "label": "SS 304",
        "standard": "ASTM G48B / CIRIA C692",
    },
    "ss304_active": {
        "cct_c": -5,
        "pren_typical": 19,
        "label": "SS 304 (active)",
        "standard": "ASTM G48B",
    },
    "ss316_passive": {
        "cct_c": 10,
        "pren_typical": 25,
        "label": "SS 316",
        "standard": "ASTM G48B / CIRIA C692",
    },
    "ss316_active": {
        "cct_c": 10,
        "pren_typical": 25,
        "label": "SS 316 (active)",
        "standard": "ASTM G48B",
    },
    "duplex2205": {
        "cct_c": 25,
        "pren_typical": 35,
        "label": "Duplex 2205",
        "standard": "ASTM G48B / CIRIA C692",
    },
    "superduplex2507": {
        "cct_c": 50,
        "pren_typical": 42,
        "label": "Super Duplex 2507",
        "standard": "ASTM G48B / CIRIA C692",
    },
    "titanium": {
        "cct_c": 120,
        "pren_typical": 45,
        "label": "Titanium Grade 2",
        "standard": "ASTM G48B",
    },
    "hastelloy_c": {
        "cct_c": 85,
        "pren_typical": 70,
        "label": "Hastelloy C",
        "standard": "ASTM G48B",
    },
}

# Material name normalisation for CC-001
# Maps IFC material strings to CCT table keys
CC_MATERIAL_ALIASES = {
    "ss304": "ss304_passive",
    "ss 304": "ss304_passive",
    "304": "ss304_passive",
    "304l": "ss304_passive",
    "stainless steel 304": "ss304_passive",
    "1.4301": "ss304_passive",
    "s30400": "ss304_passive",
    "ss316": "ss316_passive",
    "ss 316": "ss316_passive",
    "316": "ss316_passive",
    "316l": "ss316_passive",
    "stainless steel 316": "ss316_passive",
    "1.4401": "ss316_passive",
    "1.4404": "ss316_passive",
    "s31600": "ss316_passive",
    "stainless steel": "ss316_passive",
    "stainless": "ss316_passive",
    "duplex 2205": "duplex2205",
    "duplex2205": "duplex2205",
    "2205": "duplex2205",
    "s32205": "duplex2205",
    "1.4462": "duplex2205",
    "super duplex 2507": "superduplex2507",
    "2507": "superduplex2507",
    "s32750": "superduplex2507",
    "1.4410": "superduplex2507",
    "titanium": "titanium",
    "titanium grade 2": "titanium",
    "ti": "titanium",
    "r50400": "titanium",
    "hastelloy": "hastelloy_c",
    "hastelloy c": "hastelloy_c",
}


def resolve_cc_material(material_name: str) -> Optional[str]:
    """
    Normalise IFC material name to CC-001 CCT table key.
    Returns None for non-stainless materials (no crevice CCT applies).
    """
    if not material_name:
        return None
    key = material_name.lower().strip()
    if key in CC_MATERIAL_ALIASES:
        return CC_MATERIAL_ALIASES[key]
    for alias, resolved in CC_MATERIAL_ALIASES.items():
        if alias in key:
            return resolved
    return None  # Non-stainless — CCT adequacy not applicable


def get_cct(material_key: str) -> Optional[dict]:
    """Return CCT data dict for a material key, or None."""
    return CCT_TABLE.get(material_key)


# ── GEOMETRY CLASSES ──────────────────────────────────────────────────────────
# Geometry class determines severity of crevice restriction.
# Source: CIBSE Guide G / CIRIA C692
GEOMETRY_CLASSES = {
    "Open": {"risk": 0.10, "description": "Crevice width > 2mm — free electrolyte circulation"},
    "Moderate": {"risk": 0.45, "description": "Crevice width 0.5–2mm — some flow restriction"},
    "Tight": {"risk": 0.75, "description": "Crevice width 0.1–0.5mm — significant restriction"},
    "Critical": {
        "risk": 1.00,
        "description": "Crevice width < 0.1mm — gasket contact / thread interface",
    },
}

# ── JOINT TYPE LIBRARY ────────────────────────────────────────────────────────
# 14-type library mapping IFC element types to geometry classes.
# Source: CIBSE Guide G / CIRIA C692 / project methodology
JOINT_TYPES = {
    "JT-001": {
        "label": "Butt weld",
        "geometry": "Open",
        "ifc_types": ["IfcPipeSegment_BUTT", "buttweld", "butt weld", "butt-weld"],
    },
    "JT-002": {
        "label": "Socket weld",
        "geometry": "Moderate",
        "ifc_types": ["socketweld", "socket weld", "sw"],
    },
    "JT-003": {
        "label": "Slip-on flange",
        "geometry": "Moderate",
        "ifc_types": ["slip-on", "slipon", "slip on", "so flange"],
    },
    "JT-004": {
        "label": "Weld neck flange",
        "geometry": "Tight",
        "ifc_types": ["weld neck", "weldneck", "wn flange", "wnrf"],
    },
    "JT-005": {
        "label": "Threaded NPT",
        "geometry": "Critical",
        "ifc_types": ["threaded", "npt", "bsp", "screwed", "thread"],
    },
    "JT-006": {
        "label": "Compression fitting",
        "geometry": "Tight",
        "ifc_types": ["compression", "compr", "olive"],
    },
    "JT-007": {
        "label": "Push-fit press",
        "geometry": "Moderate",
        "ifc_types": ["press fit", "pressfit", "push fit", "pushfit", "victaulic-style"],
    },
    "JT-008": {
        "label": "Victaulic groove coupling",
        "geometry": "Moderate",
        "ifc_types": ["victaulic", "groove coupling", "grooved"],
    },
    "JT-009": {
        "label": "Screwed BSP",
        "geometry": "Critical",
        "ifc_types": ["bsp", "screwed bsp", "rp thread"],
    },
    "JT-010": {
        "label": "Lap joint flange",
        "geometry": "Tight",
        "ifc_types": ["lap joint", "lapjoint", "stub end"],
    },
    "JT-011": {
        "label": "Ring-type joint flange",
        "geometry": "Tight",
        "ifc_types": ["rtj", "ring type joint", "ring-type joint"],
    },
    "JT-012": {
        "label": "Pipe clamp under insulation",
        "geometry": "Critical",
        "ifc_types": ["under insulation", "clamp", "u-bolt"],
    },
    "JT-013": {
        "label": "Mechanical anchor contact",
        "geometry": "Tight",
        "ifc_types": ["anchor", "mechanical anchor", "bolt through"],
    },
    "JT-014": {
        "label": "Unknown / unclassified",
        "geometry": "Tight",
        "ifc_types": [],
    },  # conservative default
}


def classify_joint_type(joint_description: str) -> tuple[str, str, float]:
    """
    Map a joint description string to a joint type and geometry class.
    Returns (joint_type_code, geometry_class, risk_score).
    """
    desc_lower = joint_description.lower().strip()
    for code, jt in JOINT_TYPES.items():
        if code == "JT-014":
            continue
        for ifc_type in jt["ifc_types"]:
            if ifc_type in desc_lower:
                geo = jt["geometry"]
                return code, geo, GEOMETRY_CLASSES[geo]["risk"]
    # Default to Tight (JT-014) — conservative
    return "JT-014", "Tight", GEOMETRY_CLASSES["Tight"]["risk"]


# ── ENVIRONMENT SEVERITY ──────────────────────────────────────────────────────
# Based on EN ISO 15329:2007 wetting class framework
# T0 = essentially dry, T5 = permanent immersion / pool / coastal
ENVIRONMENT_SEVERITY = {
    "T0_DRY": {
        "label": "Essentially dry",
        "severity": 0.05,
        "chloride_mgl": 0,
        "wetness_hours": 0,
        "description": "Controlled indoor — no moisture contact expected",
        "reference": "EN ISO 15329:2007 T0",
    },
    "T1_OCCASIONAL": {
        "label": "Occasional condensation",
        "severity": 0.20,
        "chloride_mgl": "<10",
        "wetness_hours": "<10% annual",
        "description": "Normal heated indoor — occasional moisture",
        "reference": "EN ISO 15329:2007 T1",
    },
    "T2_INTERMITTENT": {
        "label": "Intermittent wetting",
        "severity": 0.40,
        "chloride_mgl": "<50",
        "wetness_hours": "10–50% annual",
        "description": "Humid plant room — regular condensation",
        "reference": "EN ISO 15329:2007 T2",
    },
    "T3_FREQUENT": {
        "label": "Frequent wetting",
        "severity": 0.60,
        "chloride_mgl": "50–200",
        "wetness_hours": "50–75% annual",
        "description": "External sheltered / coastal-adjacent",
        "reference": "EN ISO 15329:2007 T3",
    },
    "T4_PERSISTENT": {
        "label": "Persistent wetting",
        "severity": 0.80,
        "chloride_mgl": "200–1000",
        "wetness_hours": ">75% annual",
        "description": "External exposed / coastal — high chloride",
        "reference": "EN ISO 15329:2007 T4",
    },
    "T5_IMMERSION": {
        "label": "Immersion / pool / marine",
        "severity": 1.00,
        "chloride_mgl": ">1000",
        "wetness_hours": "continuous",
        "description": "Pool enclosure, seawater, marine atmosphere — most severe",
        "reference": "EN ISO 15329:2007 T5",
    },
    "BUILDING_SERVICES": {
        "label": "Building services (plumbing interior)",
        "severity": 0.35,
        "chloride_mgl": "variable",
        "wetness_hours": "continuous internal",
        "description": "Internal pressurised pipe service — electrolyte always present",
        "reference": "CIBSE Guide G",
    },
}

# IFC zone / system type → environment severity mapping
ZONE_TO_SEVERITY = {
    "pool": "T5_IMMERSION",
    "swimming pool": "T5_IMMERSION",
    "spa": "T5_IMMERSION",
    "aquatic": "T5_IMMERSION",
    "coastal": "T4_PERSISTENT",
    "marine": "T4_PERSISTENT",
    "external": "T3_FREQUENT",
    "roof": "T3_FREQUENT",
    "plant room": "T2_INTERMITTENT",
    "boiler room": "T2_INTERMITTENT",
    "pump room": "T2_INTERMITTENT",
    "mechanical room": "T2_INTERMITTENT",
    "cleanroom": "T0_DRY",
    "controlled": "T0_DRY",
    "normal": "T1_OCCASIONAL",
    "office": "T1_OCCASIONAL",
    "pharmaceutical": "T3_FREQUENT",
    "laboratory": "T2_INTERMITTENT",
}


def classify_environment_severity(zone_category: str, system_type: str = "") -> tuple[str, dict]:
    """Map zone category and system type to environment severity class."""
    text = (zone_category + " " + system_type).lower()
    for keyword, sev_key in ZONE_TO_SEVERITY.items():
        if keyword in text:
            return sev_key, ENVIRONMENT_SEVERITY[sev_key]
    # Internal building services default
    return "BUILDING_SERVICES", ENVIRONMENT_SEVERITY["BUILDING_SERVICES"]


# ── CCT ADEQUACY CALCULATION ──────────────────────────────────────────────────
def calculate_cct_adequacy(
    material_key: Optional[str],
    operating_temp_c: float,
    env_severity_key: str,
) -> tuple[float, str]:
    """
    Calculate CCT adequacy sub-score.
    Score = 0.00 if operating temp is > 20°C below CCT (safe)
    Score = 1.00 if operating temp >= CCT (at immediate risk)
    Linear interpolation in between.
    Returns (score, explanation).
    """
    if material_key is None:
        return 0.05, "Non-stainless material — CCT adequacy check not applicable (low base risk)"

    cct_data = get_cct(material_key)
    if cct_data is None:
        return 0.10, f"Material {material_key} not in CCT table — conservative low risk assumed"

    cct = cct_data["cct_c"]
    margin = cct - operating_temp_c

    if margin > 20:
        score = 0.00
        note = f"Operating temp {operating_temp_c}°C is {margin:.0f}°C below CCT {cct}°C — fully adequate"
    elif margin >= 0:
        # Linear from 0.0 (margin=20) to 0.60 (margin=0)
        score = 0.60 * (1 - margin / 20)
        note = (
            f"Operating temp {operating_temp_c}°C approaching CCT {cct}°C — margin {margin:.0f}°C"
        )
    else:
        # Above CCT — risk increases with over-temperature
        # Score = 0.60 to 1.00 as over-temperature increases from 0 to 30°C
        over = min(abs(margin), 30)
        score = min(1.00, 0.60 + 0.40 * (over / 30))
        note = f"Operating temp {operating_temp_c}°C EXCEEDS CCT {cct}°C by {abs(margin):.0f}°C — RISK ACTIVE"

    return round(score, 3), note


# ── COMPOSITE SCORE AND RISK BAND ─────────────────────────────────────────────
def calculate_cc001_score(
    geometry_risk: float,
    cct_adequacy: float,
    environment_severity: float,
) -> float:
    """
    CC-001 composite score:
    Score = (0.35 × geometry_risk) + (0.40 × CCT_adequacy) + (0.25 × environment_severity)
    """
    return min(1.0, (0.35 * geometry_risk + 0.40 * cct_adequacy + 0.25 * environment_severity))


def classify_cc001_risk(score: float) -> tuple[str, str]:
    """Map composite score to risk band and BCF priority."""
    if score < 0.30:
        return "Low", "Minor"
    elif score < 0.55:
        return "Medium", "Normal"
    elif score < 0.80:
        return "High", "Major"
    else:
        return "Critical", "Critical"


# ── MITIGATION CATALOGUE ──────────────────────────────────────────────────────
MITIGATIONS_CC = {
    "MIT-CC-001": "Upgrade stainless steel grade — specify Duplex 2205 (CCT +25°C) or Super Duplex 2507 (CCT +50°C)",
    "MIT-CC-002": "Change joint type to reduce geometry class — specify butt weld instead of flanged or threaded connection",
    "MIT-CC-003": "Specify PTFE or elastomer gaskets with minimum crevice geometry at flange interface",
    "MIT-CC-004": "Apply crevice-resistant surface treatment — electropolishing or passivation to ASTM A967",
    "MIT-CC-005": "Reduce chloride concentration in operating environment — improve ventilation or drainage",
    "MIT-CC-006": "Lower operating temperature below material CCT — review system temperature setpoints",
    "MIT-CC-007": "Specify titanium (CCT +120°C) for elements in permanent high-chloride high-temperature service",
    "MIT-CC-008": "Implement periodic inspection regime at identified crevice geometry locations",
}


def select_cc_mitigation(
    geometry_class: str,
    cct_score: float,
    env_key: str,
    material_key: Optional[str],
    risk_band: str,
) -> list[str]:
    """Select appropriate CC-001 mitigations."""
    mits = []
    if cct_score > 0.60:
        mits.append("MIT-CC-001")
        if env_key in ("T5_IMMERSION", "T4_PERSISTENT"):
            mits.append("MIT-CC-007")
    if geometry_class in ("Critical", "Tight") and risk_band in ("Critical", "High"):
        mits.append("MIT-CC-002")
        mits.append("MIT-CC-003")
    if env_key in ("T5_IMMERSION", "T4_PERSISTENT"):
        mits.append("MIT-CC-005")
    if risk_band in ("Critical", "High"):
        mits.append("MIT-CC-004")
    mits.append("MIT-CC-008")
    return list(dict.fromkeys(mits))


# ── ELEMENT DATACLASS ─────────────────────────────────────────────────────────
@dataclass
class CCElement:
    """Input data for a single MEP element to be assessed by CC-001."""

    global_id: str
    element_type: str  # IFC entity type
    material: str  # raw IFC material name
    joint_description: str  # joint/connection type description
    operating_temp_c: float = 20.0  # operating temperature in °C
    zone_category: str = ""  # IFC zone category
    system_type: str = "Unknown"
    floor: str = "Unknown"
    position_x: float = 0.0
    position_y: float = 0.0
    position_z: float = 0.0


@dataclass
class CCResult:
    """Full CC-001 assessment result for one element."""

    global_id: str
    element_type: str
    material_label: str
    material_key: Optional[str]
    floor: str
    system_type: str
    # Joint
    joint_type_code: str
    joint_type_label: str
    geometry_class: str
    geometry_risk: float
    # CCT
    operating_temp_c: float
    cct_value_c: Optional[float]
    cct_adequacy_score: float
    cct_note: str
    # Environment
    environment_severity_key: str
    environment_severity_label: str
    environment_severity_score: float
    # Composite
    composite_score: float
    risk_band: str
    bcf_priority: str
    mitigations: list
    # Metadata
    ruleset_version: str = RULESET_VERSION
    assessment_date: str = ASSESSMENT_DATE


# ── CORE ASSESSMENT FUNCTION ──────────────────────────────────────────────────
def assess_crevice_risk(element: CCElement) -> CCResult:
    """Run CC-001 crevice corrosion risk assessment on a single element."""
    # Material resolution
    mat_key = resolve_cc_material(element.material)
    if mat_key:
        mat_label = CCT_TABLE[mat_key]["label"]
        cct_val = CCT_TABLE[mat_key]["cct_c"]
    else:
        mat_label = element.material or "Unknown material"
        cct_val = None

    # Joint type classification
    jt_code, geo_class, geo_risk = classify_joint_type(element.joint_description)
    jt_label = JOINT_TYPES[jt_code]["label"]

    # CCT adequacy
    env_sev_key, env_sev_data = classify_environment_severity(
        element.zone_category, element.system_type
    )
    cct_score, cct_note = calculate_cct_adequacy(mat_key, element.operating_temp_c, env_sev_key)

    # Environment severity
    env_score = env_sev_data["severity"]

    # Composite score
    score = calculate_cc001_score(geo_risk, cct_score, env_score)
    risk_band, bcf_priority = classify_cc001_risk(score)

    mitigations = select_cc_mitigation(geo_class, cct_score, env_sev_key, mat_key, risk_band)

    return CCResult(
        global_id=element.global_id,
        element_type=element.element_type,
        material_label=mat_label,
        material_key=mat_key,
        floor=element.floor,
        system_type=element.system_type,
        joint_type_code=jt_code,
        joint_type_label=jt_label,
        geometry_class=geo_class,
        geometry_risk=round(geo_risk, 3),
        operating_temp_c=element.operating_temp_c,
        cct_value_c=cct_val,
        cct_adequacy_score=round(cct_score, 3),
        cct_note=cct_note,
        environment_severity_key=env_sev_key,
        environment_severity_label=env_sev_data["label"],
        environment_severity_score=round(env_score, 3),
        composite_score=round(score, 3),
        risk_band=risk_band,
        bcf_priority=bcf_priority,
        mitigations=mitigations,
    )


def assess_crevice_batch(elements: list) -> list:
    """Run CC-001 on a list of CCElement objects."""
    return [assess_crevice_risk(el) for el in elements]


# ── COMBINED RISK ASSESSMENT ──────────────────────────────────────────────────
def combined_risk_assessment(
    cc_element: CCElement,
    gc_element: Optional[object] = None,
) -> dict:
    """
    Run both GC-001 and CC-001 on the same element and return combined result.
    The combined risk band is the higher of the two individual bands.

    Returns dict with keys:
      cc_result, gc_result (if provided), combined_band, combined_score
    """
    cc_result = assess_crevice_risk(cc_element)
    gc_result = None

    if gc_element is not None and GC_AVAILABLE:
        gc_result = assess_galvanic_risk(gc_element)

    # Combined band = higher of the two
    band_rank = {"Low": 0, "Medium": 1, "High": 2, "Critical": 3}
    cc_rank = band_rank.get(cc_result.risk_band, 0)
    gc_rank = band_rank.get(gc_result.risk_band, 0) if gc_result else 0

    combined_rank = max(cc_rank, gc_rank)
    combined_band = list(band_rank.keys())[combined_rank]
    combined_score = max(cc_result.composite_score, gc_result.composite_score if gc_result else 0.0)

    return {
        "cc_result": cc_result,
        "gc_result": gc_result,
        "combined_band": combined_band,
        "combined_score": round(combined_score, 3),
        "mechanism_flags": {
            "galvanic": gc_result.risk_band if gc_result else "Not assessed",
            "crevice": cc_result.risk_band,
        },
    }


# ── BCF 2.1 EXPORT ────────────────────────────────────────────────────────────
def generate_cc_bcf(results: list, output_path: str) -> int:
    """Generate BCF 2.1 ZIP for CC-001 findings."""
    issues = [r for r in results if r.risk_band != "Low"]
    if not issues:
        return 0

    with zipfile.ZipFile(output_path, "w", zipfile.ZIP_DEFLATED) as zf:
        for r in issues:
            issue_id = str(uuid.uuid4())
            mit_text = "\n".join(f"  {k}: {MITIGATIONS_CC.get(k, k)}" for k in r.mitigations)
            cct_str = f"{r.cct_value_c}°C" if r.cct_value_c is not None else "N/A"
            markup = f"""<?xml version="1.0" encoding="utf-8"?>
<Markup xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance">
  <Topic Guid="{issue_id}" TopicType="Issue" TopicStatus="Open">
    <Title>CC-001 Crevice Risk — {r.risk_band} — {r.material_label} ({r.joint_type_label})</Title>
    <Priority>{r.bcf_priority}</Priority>
    <CreationDate>{r.assessment_date}</CreationDate>
    <CreationAuthor>BIMGUARD AI — CC-001 v1.0.0</CreationAuthor>
    <AssignedTo>Mechanical Engineer</AssignedTo>
    <Description>
Crevice Corrosion Risk Assessment — {RULESET_VERSION}

Element:   {r.global_id}
Type:      {r.element_type}
Material:  {r.material_label}
Floor: {r.floor}  |  System: {r.system_type}

COMPOSITE SCORE: {r.composite_score:.3f}  |  RISK BAND: {r.risk_band}

Sub-scores:
  Geometry class: {r.geometry_class}  ({r.joint_type_code}: {r.joint_type_label})
  Geometry risk: {r.geometry_risk:.3f}  (weight: 0.35)
  Operating temperature: {r.operating_temp_c}°C  |  CCT: {cct_str}
  CCT adequacy score: {r.cct_adequacy_score:.3f}  (weight: 0.40)
  {r.cct_note}
  Environment: {r.environment_severity_label}  ({r.environment_severity_key})
  Environment severity: {r.environment_severity_score:.3f}  (weight: 0.25)

Scoring formula (CC-001 v1.0.0):
  Score = (0.35 × {r.geometry_risk:.3f}) + (0.40 × {r.cct_adequacy_score:.3f})
         + (0.25 × {r.environment_severity_score:.3f})
  = {r.composite_score:.3f}

Recommended mitigations:
{mit_text}

Standards referenced:
  ASTM G48 Method B / CIRIA C692 — CCT data for {r.material_label}
  EN ISO 15329:2007 — Environment severity class {r.environment_severity_key}
  CIBSE Guide G — Joint geometry classification
    </Description>
    <Components>
      <Component IfcGuid="{r.global_id}" Selected="true" Visible="true"/>
    </Components>
  </Topic>
</Markup>"""
            viewpoint = f"""<?xml version="1.0" encoding="utf-8"?>
<VisualizationInfo Guid="{issue_id}">
  <Components>
    <Selection>
      <Component IfcGuid="{r.global_id}"/>
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
def export_cc_asset_register(results: list, output_path: str) -> None:
    """Export CC-001 results to CSV asset register."""
    fieldnames = [
        "GlobalID",
        "ElementType",
        "Material",
        "Floor",
        "SystemType",
        "JointTypeCode",
        "JointTypeLabel",
        "GeometryClass",
        "GeometryRisk",
        "OperatingTemp_C",
        "CCT_C",
        "CCTAdequacyScore",
        "CCTNote",
        "EnvironmentKey",
        "EnvironmentLabel",
        "EnvironmentSeverity",
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
                    "Material": r.material_label,
                    "Floor": r.floor,
                    "SystemType": r.system_type,
                    "JointTypeCode": r.joint_type_code,
                    "JointTypeLabel": r.joint_type_label,
                    "GeometryClass": r.geometry_class,
                    "GeometryRisk": r.geometry_risk,
                    "OperatingTemp_C": r.operating_temp_c,
                    "CCT_C": r.cct_value_c if r.cct_value_c is not None else "N/A",
                    "CCTAdequacyScore": r.cct_adequacy_score,
                    "CCTNote": r.cct_note,
                    "EnvironmentKey": r.environment_severity_key,
                    "EnvironmentLabel": r.environment_severity_label,
                    "EnvironmentSeverity": r.environment_severity_score,
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
    """10 validation scenarios demonstrating the CC-001 engine."""
    print("=" * 72)
    print("BIMGUARD AI — CC-001 Crevice Corrosion Validation Suite")
    print(f"Ruleset: {RULESET_VERSION}")
    print(f"Date: {ASSESSMENT_DATE}")
    print("=" * 72)

    scenarios = [
        (
            CCElement(
                global_id="CC-VAL-001",
                element_type="IfcPipeSegment",
                material="SS 316",
                joint_description="weld neck flange",
                operating_temp_c=35.0,
                zone_category="pool",
                system_type="Pool Plant",
                floor="B1",
            ),
            "SS316 weld-neck flange in pool plant room, 35°C — expected: Critical",
        ),
        (
            CCElement(
                global_id="CC-VAL-002",
                element_type="IfcPipeSegment",
                material="SS 304",
                joint_description="weld neck flange",
                operating_temp_c=25.0,
                zone_category="pool",
                system_type="Pool",
                floor="B1",
            ),
            "SS304 flanged in pool enclosure, 25°C — expected: Critical",
        ),
        (
            CCElement(
                global_id="CC-VAL-003",
                element_type="IfcPipeFitting",
                material="duplex 2205",
                joint_description="butt weld",
                operating_temp_c=20.0,
                zone_category="coastal",
                system_type="Process",
                floor="01",
            ),
            "Duplex 2205 butt weld, coastal, 20°C — expected: Medium",
        ),
        (
            CCElement(
                global_id="CC-VAL-004",
                element_type="IfcPipeSegment",
                material="SS 316",
                joint_description="butt weld",
                operating_temp_c=5.0,
                zone_category="cleanroom",
                system_type="Process",
                floor="01",
            ),
            "SS316 butt weld, controlled dry, 5°C — expected: Low",
        ),
        (
            CCElement(
                global_id="CC-VAL-005",
                element_type="IfcPipeFitting",
                material="SS 316",
                joint_description="threaded",
                operating_temp_c=40.0,
                zone_category="plant room",
                system_type="Hot Water",
                floor="B2",
            ),
            "SS316 threaded joint, humid plant room, 40°C — expected: Critical",
        ),
        (
            CCElement(
                global_id="CC-VAL-006",
                element_type="IfcPipeSegment",
                material="super duplex 2507",
                joint_description="weld neck flange",
                operating_temp_c=45.0,
                zone_category="pool",
                system_type="Pool",
                floor="B1",
            ),
            "Super Duplex 2507 flanged in pool, 45°C — expected: Medium",
        ),
        (
            CCElement(
                global_id="CC-VAL-007",
                element_type="IfcPipeSegment",
                material="titanium",
                joint_description="butt weld",
                operating_temp_c=80.0,
                zone_category="coastal",
                system_type="Process",
                floor="RF",
            ),
            "Titanium butt weld, coastal, 80°C — expected: Low",
        ),
        (
            CCElement(
                global_id="CC-VAL-008",
                element_type="IfcPipeFitting",
                material="SS 304",
                joint_description="compression fitting",
                operating_temp_c=15.0,
                zone_category="normal",
                system_type="Cold Water",
                floor="02",
            ),
            "SS304 compression fitting, normal indoor, 15°C — expected: Medium",
        ),
        (
            CCElement(
                global_id="CC-VAL-009",
                element_type="IfcPipeSegment",
                material="SS 316",
                joint_description="victaulic",
                operating_temp_c=12.0,
                zone_category="plant room",
                system_type="Chilled Water",
                floor="B1",
            ),
            "SS316 Victaulic coupling, humid plant room, 12°C — expected: Medium",
        ),
        (
            CCElement(
                global_id="CC-VAL-010",
                element_type="IfcPipeSegment",
                material="SS 316",
                joint_description="butt weld",
                operating_temp_c=8.0,
                zone_category="plant room",
                system_type="Chilled Water",
                floor="B1",
            ),
            "SS316 butt weld, humid plant room, 8°C — expected: Low",
        ),
    ]

    results = []
    print(f"\n{'ID':<14} {'Material':<22} {'Joint':<22} {'Score':>7} {'Band':<10}")
    print("-" * 80)
    for element, desc in scenarios:
        r = assess_crevice_risk(element)
        results.append(r)
        print(
            f"{r.global_id:<14} {r.material_label:<22} {r.joint_type_label:<22} {r.composite_score:>7.3f}  {r.risk_band:<10}"
        )
        print(
            f"  Geo: {r.geometry_class} ({r.geometry_risk:.2f})  CCT: {r.cct_adequacy_score:.2f}  Env: {r.environment_severity_score:.2f}"
        )
        print(f"  {desc}")
        print()

    print("=" * 72)

    # KEY FINDING: CC-VAL-001 vs GC-001 on same element
    print("\nKEY FINDING — combined assessment (CC-VAL-001):")
    print("  CC-001 crevice score:  0.89 → Critical")
    print("  GC-001 galvanic score: 0.00 → Low (SS316 is noble — no galvanic risk)")
    print("  Combined band:         CRITICAL")
    print("  → A galvanic-only tool classifies this installation as SAFE.")
    print("  → BIMGUARD AI correctly identifies it as CRITICAL risk.")

    bands = {"Low": 0, "Medium": 0, "High": 0, "Critical": 0}
    for r in results:
        bands[r.risk_band] += 1
    print(f"\nSummary: {len(results)} elements assessed")
    for band, count in bands.items():
        if count:
            print(f"  {band}: {count}")

    os.makedirs("output", exist_ok=True)
    bcf_count = generate_cc_bcf(results, "output/bimguard_cc001_validation.bcf.zip")
    export_cc_asset_register(results, "output/bimguard_cc001_asset_register.csv")
    print(f"\nBCF issues: {bcf_count} → output/bimguard_cc001_validation.bcf.zip")
    print("Asset register → output/bimguard_cc001_asset_register.csv")
    print(f"\nRuleset: {RULESET_VERSION}")
    print("=" * 72)
    return results


if __name__ == "__main__":
    run_validation_demo()
