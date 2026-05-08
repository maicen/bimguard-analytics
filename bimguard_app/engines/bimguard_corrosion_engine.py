"""
BIMGUARD AI — Galvanic Corrosion Engine
Ruleset: BIMGUARD-GC-001 v1.0.0

Standards referenced:
  - NASA-STD-6012 (voltage thresholds by environment class)
  - WorldStainless / Euro Inox (2025) (galvanic series, corrosion rate data)
  - AUCSC Basic Corrosion Course (2024) (galvanic series, electrolyte conductivity)
  - IMOA Design Manual 4th Ed. (PREN formula and grade selection)
  - Prosoco Technical Note 104 (area ratio analysis)
  - American Galvanizers Association (coating life data)
  - ISO 19650 (BIM information management, IFC property set framework)
  - buildingSMART BCF 2.1 (issue tracking specification)

Weighted composite score:
  Score_GC = (0.50 × voltage_risk)
            + (0.30 × area_ratio_risk)
            + (0.20 × environment_multiplier)

Risk bands:
  Low      < 0.35
  Medium   0.35 – 0.65
  High     0.65 – 0.85
  Critical > 0.85
"""

import csv
import os
import uuid
import zipfile
from dataclasses import dataclass
from datetime import datetime
from typing import Optional

# ── VERSION ───────────────────────────────────────────────────────────────────
RULESET_VERSION = "BIMGUARD-GC-001 v1.0.0"
ASSESSMENT_DATE = datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ")

# ── GALVANIC SERIES TABLE ─────────────────────────────────────────────────────
# Corrosion potential in seawater (V vs. Ag/AgCl reference)
# Source: WorldStainless / Euro Inox (2025) and AUCSC Basic Corrosion Course (2024)
# Lower value = more noble (cathodic) — corrodes less
# Higher value = more active (anodic) — corrodes preferentially
GALVANIC_SERIES = {
    "platinum": {"potential": 0.00, "label": "Platinum", "noble": True},
    "gold": {"potential": 0.02, "label": "Gold", "noble": True},
    "graphite": {"potential": 0.03, "label": "Graphite", "noble": True},
    "titanium": {"potential": 0.05, "label": "Titanium", "noble": True},
    "ss316_passive": {"potential": 0.08, "label": "SS 316 (passive)", "noble": True},
    "ss304_passive": {"potential": 0.12, "label": "SS 304 (passive)", "noble": True},
    "hastelloy_c": {"potential": 0.14, "label": "Hastelloy C", "noble": True},
    "silver_solder": {"potential": 0.18, "label": "Silver solder", "noble": True},
    "ss316_active": {"potential": 0.22, "label": "SS 316 (active)", "noble": False},
    "copper": {"potential": 0.28, "label": "Copper", "noble": True},
    "brass": {"potential": 0.32, "label": "Brass (70/30)", "noble": False},
    "bronze": {"potential": 0.34, "label": "Bronze", "noble": False},
    "ss304_active": {"potential": 0.38, "label": "SS 304 (active)", "noble": False},
    "cast_iron": {"potential": 0.52, "label": "Cast iron", "noble": False},
    "carbon_steel": {"potential": 0.55, "label": "Carbon / mild steel", "noble": False},
    "aluminium": {"potential": 0.70, "label": "Aluminium alloys", "noble": False},
    "cadmium": {"potential": 0.75, "label": "Cadmium", "noble": False},
    "zinc": {"potential": 0.80, "label": "Zinc", "noble": False},
    "galv_steel": {"potential": 0.82, "label": "Galvanised steel", "noble": False},
    "magnesium": {"potential": 0.95, "label": "Magnesium alloys", "noble": False},
}

# Material name normalisation map — maps IFC material name variants to galvanic series keys
MATERIAL_ALIASES = {
    # Stainless 316
    "ss316": "ss316_passive",
    "ss 316": "ss316_passive",
    "316": "ss316_passive",
    "316l": "ss316_passive",
    "316l stainless": "ss316_passive",
    "stainless steel 316": "ss316_passive",
    "stainless 316": "ss316_passive",
    "1.4401": "ss316_passive",
    "1.4404": "ss316_passive",
    "s31600": "ss316_passive",
    # Stainless 304
    "ss304": "ss304_passive",
    "ss 304": "ss304_passive",
    "304": "ss304_passive",
    "304l": "ss304_passive",
    "stainless steel 304": "ss304_passive",
    "1.4301": "ss304_passive",
    "s30400": "ss304_passive",
    # Stainless generic
    "stainless steel": "ss316_passive",
    "stainless": "ss316_passive",
    # Duplex / super duplex → map to passive SS316 equivalent potential range
    "duplex 2205": "ss316_passive",
    "2205": "ss316_passive",
    "duplex2205": "ss316_passive",
    "s32205": "ss316_passive",
    "1.4462": "ss316_passive",
    "super duplex 2507": "ss316_passive",
    "2507": "ss316_passive",
    # Carbon steel
    "carbon steel": "carbon_steel",
    "mild steel": "carbon_steel",
    "cs": "carbon_steel",
    "ms": "carbon_steel",
    "steel": "carbon_steel",
    "black steel": "carbon_steel",
    "erw": "carbon_steel",
    # Galvanised
    "galvanised steel": "galv_steel",
    "galvanized steel": "galv_steel",
    "galvanised": "galv_steel",
    "galvanized": "galv_steel",
    "hot dip galvanised": "galv_steel",
    # Copper
    "copper": "copper",
    "cu": "copper",
    "copper tube": "copper",
    "copper pipe": "copper",
    "r220": "copper",
    "r250": "copper",
    # Brass
    "brass": "brass",
    "gunmetal": "brass",
    # Cast iron
    "cast iron": "cast_iron",
    "ci": "cast_iron",
    "grey iron": "cast_iron",
    "ductile iron": "cast_iron",
    # Aluminium
    "aluminium": "aluminium",
    "aluminum": "aluminium",
    "al": "aluminium",
    "6061": "aluminium",
    # Titanium
    "titanium": "titanium",
    "ti": "titanium",
    "titanium grade 2": "titanium",
    # Non-metallic (no galvanic risk)
    "pvc": None,
    "cpvc": None,
    "hdpe": None,
    "upvc": None,
    "abs": None,
    "pp": None,
    "pvdf": None,
}


def resolve_material(material_name: str) -> Optional[str]:
    """
    Normalise an IFC material name string to a galvanic series key.
    Returns None for non-metallic materials (no galvanic risk).
    Returns 'carbon_steel' as fallback for unrecognised metallic strings.
    """
    if not material_name:
        return "carbon_steel"  # conservative default
    key = material_name.lower().strip()
    if key in MATERIAL_ALIASES:
        return MATERIAL_ALIASES[key]
    # Substring matching for unrecognised variants
    for alias, resolved in MATERIAL_ALIASES.items():
        if alias in key:
            return resolved
    # Default: treat as carbon steel (conservative)
    return "carbon_steel"


def get_galvanic_potential(material_key: Optional[str]) -> Optional[float]:
    """Return the galvanic potential for a resolved material key."""
    if material_key is None:
        return None
    return GALVANIC_SERIES.get(material_key, {}).get("potential")


# ── ENVIRONMENT CLASSES ───────────────────────────────────────────────────────
# Voltage thresholds per NASA-STD-6012
ENVIRONMENT_CLASSES = {
    "E1_CONTROLLED": {
        "label": "Fully controlled / dry indoor",
        "voltage_threshold": 0.50,
        "multiplier": 0.20,
        "description": "Temperature and humidity controlled — minimal electrolyte risk",
    },
    "E2_NORMAL": {
        "label": "Normal heated indoor",
        "voltage_threshold": 0.25,
        "multiplier": 0.40,
        "description": "Standard building services environment — occasional condensation",
    },
    "E3_HUMID": {
        "label": "Humid plant room",
        "voltage_threshold": 0.15,
        "multiplier": 0.65,
        "description": "High humidity, regular condensation — significant electrolyte risk",
    },
    "E4_SHELTERED": {
        "label": "External sheltered",
        "voltage_threshold": 0.15,
        "multiplier": 0.70,
        "description": "External but sheltered from direct rainfall",
    },
    "E5_EXPOSED": {
        "label": "External exposed",
        "voltage_threshold": 0.10,
        "multiplier": 0.85,
        "description": "Direct weather exposure — continuous moisture risk",
    },
    "E6_POOL": {
        "label": "Pool or spa enclosure",
        "voltage_threshold": 0.10,
        "multiplier": 0.90,
        "description": "Chloride-rich humid atmosphere — aggressive galvanic environment",
    },
    "E7_COASTAL": {
        "label": "Coastal or marine",
        "voltage_threshold": 0.05,
        "multiplier": 1.00,
        "description": "Salt air or seawater — most aggressive environment",
    },
}

# IFC zone category → environment class mapping
ZONE_TO_ENV = {
    "pool": "E6_POOL",
    "swimming pool": "E6_POOL",
    "spa": "E6_POOL",
    "plant room": "E3_HUMID",
    "plantroom": "E3_HUMID",
    "mechanical room": "E3_HUMID",
    "boiler room": "E3_HUMID",
    "pump room": "E3_HUMID",
    "external": "E5_EXPOSED",
    "roof": "E5_EXPOSED",
    "car park": "E4_SHELTERED",
    "coastal": "E7_COASTAL",
    "marine": "E7_COASTAL",
    "cleanroom": "E1_CONTROLLED",
    "laboratory": "E1_CONTROLLED",
    "server room": "E1_CONTROLLED",
    "data centre": "E1_CONTROLLED",
}


def classify_environment(zone_category: str = "") -> tuple[str, dict]:
    """Map an IFC zone category string to an environment class."""
    cat = zone_category.lower().strip()
    for keyword, env_key in ZONE_TO_ENV.items():
        if keyword in cat:
            return env_key, ENVIRONMENT_CLASSES[env_key]
    return "E2_NORMAL", ENVIRONMENT_CLASSES["E2_NORMAL"]


# ── VOLTAGE RISK CALCULATION ──────────────────────────────────────────────────
def calculate_voltage_risk(
    potential_anode: float,
    potential_cathode: float,
    env_threshold: float,
) -> float:
    """
    Calculate normalised voltage risk score (0.0–1.0).
    Score is proportional to how far the gap exceeds the threshold.
    Gap at 0V = 0.00, gap at threshold = 0.50, gap at 2× threshold = 1.00.
    """
    gap = abs(potential_anode - potential_cathode)
    if env_threshold <= 0:
        return 1.0
    ratio = gap / env_threshold
    return min(1.0, ratio / 2.0)


# ── AREA RATIO RISK BANDS ─────────────────────────────────────────────────────
# Source: Prosoco Technical Note 104 / AUCSC Basic Corrosion Course
AREA_RATIO_BANDS = [
    {"label": "Favourable", "min_ratio": 5.0, "max_ratio": float("inf"), "risk": 0.20},
    {"label": "Acceptable", "min_ratio": 2.0, "max_ratio": 5.0, "risk": 0.40},
    {"label": "Moderate", "min_ratio": 0.5, "max_ratio": 2.0, "risk": 0.60},
    {"label": "Unfavourable", "min_ratio": 0.1, "max_ratio": 0.5, "risk": 0.80},
    {"label": "Critical", "min_ratio": 0.0, "max_ratio": 0.1, "risk": 1.00},
]


def classify_area_ratio(anode_area_m2: float, cathode_area_m2: float) -> tuple[str, float]:
    """
    Classify anode-to-cathode area ratio into a risk band.
    Returns (band_label, risk_score).
    """
    if cathode_area_m2 <= 0:
        return "Critical", 1.00
    ratio = anode_area_m2 / cathode_area_m2
    for band in AREA_RATIO_BANDS:
        if band["min_ratio"] <= ratio < band["max_ratio"]:
            return band["label"], band["risk"]
        if ratio >= band["min_ratio"] and band["max_ratio"] == float("inf"):
            return band["label"], band["risk"]
    return "Critical", 1.00


# ── PREN ADEQUACY CHECK ───────────────────────────────────────────────────────
# Source: IMOA Design Manual 4th Ed.
PREN_THRESHOLDS = {
    "E1_CONTROLLED": 18,  # SS304 adequate
    "E2_NORMAL": 18,
    "E3_HUMID": 25,  # SS316 required
    "E4_SHELTERED": 25,
    "E5_EXPOSED": 32,  # Duplex 2205+ required
    "E6_POOL": 32,
    "E7_COASTAL": 40,  # Super Duplex 2507+ required
}

PREN_VALUES = {
    "ss304_passive": 18,
    "ss304_active": 18,
    "ss316_passive": 25,
    "ss316_active": 25,
    # Duplex and super duplex mapped to ss316 key in aliases, but store actual PREN
}


def check_pren_adequacy(material_key: str, env_class: str) -> tuple[bool, str]:
    """
    Check PREN adequacy for stainless steel materials.
    Returns (adequate: bool, note: str).
    """
    pren = PREN_VALUES.get(material_key)
    if pren is None:
        return True, "Non-stainless material — PREN check not applicable"
    threshold = PREN_THRESHOLDS.get(env_class, 18)
    adequate = pren >= threshold
    note = (
        f"PREN {pren} {'≥' if adequate else '<'} required {threshold} "
        f"for {ENVIRONMENT_CLASSES[env_class]['label']}"
    )
    return adequate, note


# ── COMPOSITE SCORE AND RISK BAND ─────────────────────────────────────────────
def calculate_gc001_score(
    voltage_risk: float,
    area_ratio_risk: float,
    environment_multiplier: float,
) -> float:
    """
    GC-001 composite score formula:
    Score = (0.50 × voltage_risk) + (0.30 × area_ratio_risk) + (0.20 × environment_multiplier)
    """
    return min(1.0, (0.50 * voltage_risk + 0.30 * area_ratio_risk + 0.20 * environment_multiplier))


def classify_gc001_risk(score: float) -> tuple[str, str]:
    """Map composite score to risk band and BCF priority."""
    if score < 0.35:
        return "Low", "Minor"
    elif score < 0.65:
        return "Medium", "Normal"
    elif score < 0.85:
        return "High", "Major"
    else:
        return "Critical", "Critical"


# ── MITIGATION CATALOGUE ──────────────────────────────────────────────────────
MITIGATIONS_GC = {
    "MIT-GC-001": "Install dielectric isolation gaskets at all contact points between dissimilar metals",
    "MIT-GC-002": "Specify non-conductive spacers or sleeves between dissimilar metal surfaces",
    "MIT-GC-003": "Replace less noble metal with grade compatible with adjacent material",
    "MIT-GC-004": "Apply protective organic coating to both metallic surfaces at contact zone",
    "MIT-GC-005": "Install cathodic protection system — sacrificial anode or impressed current",
    "MIT-GC-006": "Increase separation distance to prevent moisture bridge formation",
    "MIT-GC-007": "Upgrade stainless steel grade to meet PREN requirement for environment class",
    "MIT-GC-008": "Replace galvanised steel fittings with SS304 or SS316 in this zone",
    "MIT-GC-009": "Use corrosion-inhibiting sealant at all dissimilar metal joints",
    "MIT-GC-010": "Implement corrosion monitoring programme at identified high-risk junctions",
}


def select_gc_mitigation(
    anode_key: str,
    cathode_key: str,
    risk_band: str,
    pren_adequate: bool,
) -> list[str]:
    """Select appropriate GC-001 mitigations based on material pairing and risk."""
    mits = []
    if not pren_adequate:
        mits.append("MIT-GC-007")
    if anode_key == "galv_steel" or cathode_key == "galv_steel":
        mits.append("MIT-GC-008")
    if risk_band in ("Critical", "High"):
        mits.append("MIT-GC-001")
        mits.append("MIT-GC-002")
    elif risk_band == "Medium":
        mits.append("MIT-GC-004")
    mits.append("MIT-GC-010")
    return list(dict.fromkeys(mits))


# ── ELEMENT DATACLASS ─────────────────────────────────────────────────────────
@dataclass
class GCElement:
    """Input data for a single MEP element pair to be assessed by GC-001."""

    global_id_anode: str
    global_id_cathode: str
    material_anode: str  # raw IFC material name string
    material_cathode: str  # raw IFC material name string
    anode_area_m2: float = 1.0  # surface area of anode element
    cathode_area_m2: float = 1.0  # surface area of cathode element
    zone_category: str = ""  # IFC zone category for environment classification
    floor: str = "Unknown"
    system_type: str = "Unknown"
    position_x: float = 0.0
    position_y: float = 0.0
    position_z: float = 0.0


@dataclass
class GCResult:
    """Full GC-001 assessment result for one element pair."""

    global_id_anode: str
    global_id_cathode: str
    material_anode_label: str
    material_cathode_label: str
    material_anode_key: str
    material_cathode_key: str
    floor: str
    system_type: str
    # Sub-scores
    voltage_gap_v: float
    env_threshold_v: float
    voltage_risk: float
    area_ratio: float
    area_ratio_band: str
    area_ratio_risk: float
    environment_class: str
    environment_label: str
    environment_multiplier: float
    # PREN
    pren_adequate: bool
    pren_note: str
    # Composite
    composite_score: float
    risk_band: str
    bcf_priority: str
    mitigations: list
    # Metadata
    ruleset_version: str = RULESET_VERSION
    assessment_date: str = ASSESSMENT_DATE


# ── CORE ASSESSMENT FUNCTION ──────────────────────────────────────────────────
def assess_galvanic_risk(element: GCElement) -> GCResult:
    """
    Run GC-001 galvanic corrosion risk assessment on a single element pair.
    """
    # Resolve materials
    anode_key = resolve_material(element.material_anode)
    cathode_key = resolve_material(element.material_cathode)

    # Handle non-metallic materials
    anode_potential = get_galvanic_potential(anode_key)
    cathode_potential = get_galvanic_potential(cathode_key)

    # Determine which is actually the anode (less noble = higher potential)
    if (
        anode_potential is not None
        and cathode_potential is not None
        and anode_potential < cathode_potential
    ):
        # Swap so anode is always the less noble (higher potential)
        anode_key, cathode_key = cathode_key, anode_key
        anode_potential, cathode_potential = cathode_potential, anode_potential
        element.global_id_anode, element.global_id_cathode = (
            element.global_id_cathode,
            element.global_id_anode,
        )

    # Environment classification
    env_class, env_data = classify_environment(element.zone_category)
    threshold = env_data["voltage_threshold"]
    multiplier = env_data["multiplier"]

    # Voltage gap
    if anode_potential is not None and cathode_potential is not None:
        gap = abs(anode_potential - cathode_potential)
        v_risk = calculate_voltage_risk(anode_potential, cathode_potential, threshold)
    else:
        gap = 0.0
        v_risk = 0.0  # non-metallic — no galvanic risk

    # Area ratio
    ar_band, ar_risk = classify_area_ratio(element.anode_area_m2, element.cathode_area_m2)

    # PREN check
    pren_ok, pren_note = check_pren_adequacy(anode_key or "", env_class)
    if cathode_key:
        pren_ok_c, pren_note_c = check_pren_adequacy(cathode_key, env_class)
        if not pren_ok_c:
            pren_ok = False
            pren_note = pren_note_c

    # Composite score
    score = calculate_gc001_score(v_risk, ar_risk, multiplier)

    # PREN failure escalates minimum score to Medium
    if not pren_ok and score < 0.35:
        score = 0.35

    risk_band, bcf_priority = classify_gc001_risk(score)
    mitigations = select_gc_mitigation(anode_key or "", cathode_key or "", risk_band, pren_ok)

    anode_label = GALVANIC_SERIES.get(anode_key, {}).get("label", element.material_anode)
    cathode_label = GALVANIC_SERIES.get(cathode_key, {}).get("label", element.material_cathode)

    return GCResult(
        global_id_anode=element.global_id_anode,
        global_id_cathode=element.global_id_cathode,
        material_anode_label=anode_label,
        material_cathode_label=cathode_label,
        material_anode_key=anode_key or "unknown",
        material_cathode_key=cathode_key or "unknown",
        floor=element.floor,
        system_type=element.system_type,
        voltage_gap_v=round(gap, 4),
        env_threshold_v=threshold,
        voltage_risk=round(v_risk, 3),
        area_ratio=round(element.anode_area_m2 / max(element.cathode_area_m2, 1e-6), 3),
        area_ratio_band=ar_band,
        area_ratio_risk=round(ar_risk, 3),
        environment_class=env_class,
        environment_label=env_data["label"],
        environment_multiplier=round(multiplier, 3),
        pren_adequate=pren_ok,
        pren_note=pren_note,
        composite_score=round(score, 3),
        risk_band=risk_band,
        bcf_priority=bcf_priority,
        mitigations=mitigations,
    )


def assess_galvanic_batch(elements: list) -> list:
    """Run GC-001 on a list of GCElement pairs."""
    return [assess_galvanic_risk(el) for el in elements]


# ── BCF 2.1 EXPORT ────────────────────────────────────────────────────────────
def generate_gc_bcf(results: list, output_path: str) -> int:
    """
    Generate BCF 2.1 compliant ZIP for GC-001 findings.
    Only Medium, High, and Critical results generate BCF issues.
    Returns count of issues generated.
    """
    issues = [r for r in results if r.risk_band != "Low"]
    if not issues:
        return 0

    with zipfile.ZipFile(output_path, "w", zipfile.ZIP_DEFLATED) as zf:
        for r in issues:
            issue_id = str(uuid.uuid4())
            mit_text = "\n".join(f"  {k}: {MITIGATIONS_GC.get(k, k)}" for k in r.mitigations)
            markup = f"""<?xml version="1.0" encoding="utf-8"?>
<Markup xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance">
  <Topic Guid="{issue_id}" TopicType="Issue" TopicStatus="Open">
    <Title>GC-001 Galvanic Risk — {r.risk_band} — {r.material_anode_label} / {r.material_cathode_label}</Title>
    <Priority>{r.bcf_priority}</Priority>
    <CreationDate>{r.assessment_date}</CreationDate>
    <CreationAuthor>BIMGUARD AI — GC-001 v1.0.0</CreationAuthor>
    <AssignedTo>Mechanical Engineer</AssignedTo>
    <Description>
Galvanic Corrosion Risk Assessment — {RULESET_VERSION}

Anode element:   {r.global_id_anode}  ({r.material_anode_label})
Cathode element: {r.global_id_cathode}  ({r.material_cathode_label})
Floor: {r.floor}  |  System: {r.system_type}

COMPOSITE SCORE: {r.composite_score:.3f}  |  RISK BAND: {r.risk_band}

Sub-scores:
  Voltage gap: {r.voltage_gap_v:.4f}V  (threshold: {r.env_threshold_v}V)
  Voltage risk: {r.voltage_risk:.3f}  (weight: 0.50)
  Area ratio: {r.area_ratio:.3f}  ({r.area_ratio_band})
  Area ratio risk: {r.area_ratio_risk:.3f}  (weight: 0.30)
  Environment: {r.environment_label}  ({r.environment_class})
  Environment multiplier: {r.environment_multiplier:.3f}  (weight: 0.20)

PREN adequacy: {"PASS" if r.pren_adequate else "FAIL"}  — {r.pren_note}

Scoring formula (GC-001 v1.0.0):
  Score = (0.50 × {r.voltage_risk:.3f}) + (0.30 × {r.area_ratio_risk:.3f})
         + (0.20 × {r.environment_multiplier:.3f})
  = {r.composite_score:.3f}

Recommended mitigations:
{mit_text}

Standards referenced:
  NASA-STD-6012 — Voltage threshold: {r.env_threshold_v}V for {r.environment_label}
  IMOA Design Manual 4th Ed. — PREN adequacy check
  WorldStainless / Euro Inox (2025) — Galvanic series data
    </Description>
    <Components>
      <Component IfcGuid="{r.global_id_anode}" Selected="true" Visible="true"/>
      <Component IfcGuid="{r.global_id_cathode}" Selected="true" Visible="true"/>
    </Components>
  </Topic>
</Markup>"""
            viewpoint = f"""<?xml version="1.0" encoding="utf-8"?>
<VisualizationInfo Guid="{issue_id}">
  <Components>
    <Selection>
      <Component IfcGuid="{r.global_id_anode}"/>
      <Component IfcGuid="{r.global_id_cathode}"/>
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
def export_gc_asset_register(results: list, output_path: str) -> None:
    """Export GC-001 results to CSV asset register."""
    fieldnames = [
        "AnodeGlobalID",
        "CathodeGlobalID",
        "AnodeMaterial",
        "CathodeMaterial",
        "Floor",
        "SystemType",
        "VoltageGap_V",
        "EnvThreshold_V",
        "VoltageRisk",
        "AreaRatio",
        "AreaRatioBand",
        "AreaRatioRisk",
        "EnvironmentClass",
        "EnvironmentLabel",
        "EnvMultiplier",
        "PRENAdequate",
        "PRENNote",
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
                    "AnodeGlobalID": r.global_id_anode,
                    "CathodeGlobalID": r.global_id_cathode,
                    "AnodeMaterial": r.material_anode_label,
                    "CathodeMaterial": r.material_cathode_label,
                    "Floor": r.floor,
                    "SystemType": r.system_type,
                    "VoltageGap_V": r.voltage_gap_v,
                    "EnvThreshold_V": r.env_threshold_v,
                    "VoltageRisk": r.voltage_risk,
                    "AreaRatio": r.area_ratio,
                    "AreaRatioBand": r.area_ratio_band,
                    "AreaRatioRisk": r.area_ratio_risk,
                    "EnvironmentClass": r.environment_class,
                    "EnvironmentLabel": r.environment_label,
                    "EnvMultiplier": r.environment_multiplier,
                    "PRENAdequate": r.pren_adequate,
                    "PRENNote": r.pren_note,
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
    """5 validation scenarios demonstrating the GC-001 engine."""
    print("=" * 72)
    print("BIMGUARD AI — GC-001 Galvanic Corrosion Validation Suite")
    print(f"Ruleset: {RULESET_VERSION}")
    print(f"Date: {ASSESSMENT_DATE}")
    print("=" * 72)

    scenarios = [
        (
            GCElement(
                global_id_anode="GC-VAL-001A",
                global_id_cathode="GC-VAL-001B",
                material_anode="copper",
                material_cathode="galvanised steel",
                anode_area_m2=2.5,
                cathode_area_m2=12.0,
                zone_category="plant room",
                floor="B1",
                system_type="Chilled Water",
            ),
            "Copper pipe + galvanised steel bracket, humid plant room — expected: Critical",
        ),
        (
            GCElement(
                global_id_anode="GC-VAL-002A",
                global_id_cathode="GC-VAL-002B",
                material_anode="SS 316",
                material_cathode="stainless steel 304",
                anode_area_m2=3.0,
                cathode_area_m2=3.0,
                zone_category="cleanroom",
                floor="01",
                system_type="Process",
            ),
            "SS316 pipe + SS304 fittings, controlled environment — expected: Low",
        ),
        (
            GCElement(
                global_id_anode="GC-VAL-003A",
                global_id_cathode="GC-VAL-003B",
                material_anode="carbon steel",
                material_cathode="aluminium",
                anode_area_m2=5.0,
                cathode_area_m2=1.0,
                zone_category="external",
                floor="RF",
                system_type="Drainage",
            ),
            "Carbon steel pipe + aluminium bracket, external exposed — expected: High",
        ),
        (
            GCElement(
                global_id_anode="GC-VAL-004A",
                global_id_cathode="GC-VAL-004B",
                material_anode="titanium",
                material_cathode="SS 316",
                anode_area_m2=2.0,
                cathode_area_m2=2.0,
                zone_category="pool",
                floor="B1",
                system_type="Pool",
            ),
            "Titanium + SS316 in pool enclosure — expected: Low (both noble)",
        ),
        (
            GCElement(
                global_id_anode="GC-VAL-005A",
                global_id_cathode="GC-VAL-005B",
                material_anode="brass",
                material_cathode="carbon steel",
                anode_area_m2=0.8,
                cathode_area_m2=8.0,
                zone_category="normal heated indoor",
                floor="02",
                system_type="LTHW",
            ),
            "Brass valve + carbon steel pipe, normal indoor — expected: Medium",
        ),
    ]

    results = []
    print(f"\n{'ID':<16} {'Pairing':<38} {'Score':>7} {'Band':<10}")
    print("-" * 80)

    for element, desc in scenarios:
        r = assess_galvanic_risk(element)
        results.append(r)
        pairing = f"{r.material_anode_label} / {r.material_cathode_label}"
        print(f"{r.global_id_anode:<16} {pairing:<38} {r.composite_score:>7.3f}  {r.risk_band:<10}")
        print(
            f"  Gap: {r.voltage_gap_v:.4f}V  |  Threshold: {r.env_threshold_v}V  |  "
            f"Env: {r.environment_class}  |  PREN: {'OK' if r.pren_adequate else 'FAIL'}"
        )
        print(f"  {desc}")
        print()

    print("=" * 72)
    bands = {"Low": 0, "Medium": 0, "High": 0, "Critical": 0}
    for r in results:
        bands[r.risk_band] += 1
    print(f"\nSummary: {len(results)} pairs assessed")
    for band, count in bands.items():
        if count:
            print(f"  {band}: {count}")

    os.makedirs("output", exist_ok=True)
    bcf_count = generate_gc_bcf(results, "output/bimguard_gc001_validation.bcf.zip")
    export_gc_asset_register(results, "output/bimguard_gc001_asset_register.csv")
    print(f"\nBCF issues: {bcf_count} → output/bimguard_gc001_validation.bcf.zip")
    print("Asset register → output/bimguard_gc001_asset_register.csv")
    print(f"\nRuleset: {RULESET_VERSION}")
    print("=" * 72)
    return results


if __name__ == "__main__":
    run_validation_demo()
