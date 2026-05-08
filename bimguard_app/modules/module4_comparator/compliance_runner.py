"""
BIMGUARD AI — Compliance Runner
Connects IFC service elements to GC-001 and CC-001 engines.
Returns unified results ready for BCF generation and dashboard.
"""

from ..module2_ifc_read.ifc_parser import ServiceElement

# ── Galvanic potential table ────────────────────────────────────────────────
GP = {
    "Gold": 0.00,
    "Graphite": 0.05,
    "Titanium": 0.12,
    "SS_super_duplex_2507": 0.14,
    "SS_duplex_2205": 0.16,
    "SS_316_passive": 0.18,
    "SS_304_passive": 0.20,
    "Monel": 0.25,
    "Copper": 0.30,
    "Brass_naval": 0.36,
    "Bronze": 0.38,
    "Lead": 0.55,
    "Carbon_steel_mild": 0.70,
    "Cast_iron": 0.75,
    "Galvanized_steel": 0.85,
    "Aluminum_alloy_6063": 0.90,
    "Zinc": 1.05,
}

PREN = {
    "SS_304_passive": 18,
    "SS_316_passive": 24,
    "SS_duplex_2205": 35,
    "SS_super_duplex_2507": 42,
}

PREN_MIN = {
    "interior_dry": 10,
    "interior_conditioned": 13,
    "urban_exterior": 18,
    "industrial": 22,
    "swimming_pool": 26,
    "coastal": 24,
    "marine_splash": 40,
}

ENVS = {
    "interior_dry": {"mult": 0.20, "tier": "controlled"},
    "interior_conditioned": {"mult": 0.30, "tier": "controlled"},
    "urban_exterior": {"mult": 0.60, "tier": "normal"},
    "industrial": {"mult": 0.80, "tier": "normal"},
    "swimming_pool": {"mult": 1.10, "tier": "harsh"},
    "coastal": {"mult": 1.20, "tier": "harsh"},
    "marine_splash": {"mult": 1.50, "tier": "harsh"},
}

V_THRESH = {"controlled": 0.50, "normal": 0.25, "harsh": 0.15}

CCT = {
    "SS_304_passive": -5,
    "SS_316_passive": 10,
    "SS_duplex_2205": 25,
    "SS_super_duplex_2507": 50,
    "Titanium": 120,
}
CCT_MIN = {
    "interior_dry": -5,
    "interior_conditioned": 10,
    "urban_exterior": 10,
    "industrial": 25,
    "swimming_pool": 25,
    "coastal": 25,
    "marine_splash": 50,
}

GEO = {"open": 0.10, "moderate": 0.45, "tight": 0.75, "critical": 1.00}

JOINT_GEO = {
    "JT-001": "tight",
    "JT-002": "moderate",
    "JT-003": "tight",
    "JT-004": "tight",
    "JT-005": "tight",
    "JT-006": "moderate",
    "JT-007": "open",
    "JT-008": "tight",
    "JT-009": "critical",
    "JT-010": "tight",
    "JT-011": "open",
    "JT-012": "tight",
    "JT-013": "tight",
    "JT-014": "critical",
}

CC_SEV = {
    "interior_dry": 0.10,
    "interior_conditioned": 0.30,
    "urban_exterior": 0.50,
    "industrial": 0.70,
    "swimming_pool": 0.90,
    "coastal": 0.85,
    "marine_splash": 1.00,
}


def _galvanic_band(s):
    return "LOW" if s < 0.35 else "MEDIUM" if s < 0.65 else "HIGH" if s < 0.85 else "CRITICAL"


def _crevice_band(s):
    return "LOW" if s < 0.30 else "MEDIUM" if s < 0.55 else "HIGH" if s < 0.80 else "CRITICAL"


def _band_int(b):
    return {"LOW": 0, "MEDIUM": 1, "HIGH": 2, "CRITICAL": 3}.get(b, 0)


def _galvanic_score(el: ServiceElement) -> tuple:
    env = ENVS.get(el.location_tag, ENVS["interior_dry"])
    pot_a = GP.get(el.material_a, 0.5)
    pot_b = GP.get(el.material_b, 0.5)
    gap = abs(pot_a - pot_b)
    thr = V_THRESH[env["tier"]]
    v_risk = min(gap / thr, 1.0)

    ratio = el.anode_area_m2 / el.cathode_area_m2 if el.cathode_area_m2 > 0 else 1
    a_risk = (
        0
        if ratio >= 1
        else 0.2
        if ratio >= 0.5
        else 0.5
        if ratio >= 0.1
        else 0.8
        if ratio >= 0.01
        else 1.0
    )

    env_n = min(env["mult"] / 1.5, 1.0)
    score = min(0.50 * v_risk + 0.30 * a_risk + 0.20 * env_n, 1.0)

    # PREN check
    pren = PREN.get(el.material_a) or PREN.get(el.material_b)
    pren_min = PREN_MIN.get(el.location_tag)
    pren_fail = bool(pren and pren_min and pren < pren_min)

    anodic = el.material_a if pot_a >= pot_b else el.material_b

    return round(score, 4), _galvanic_band(score), gap, thr, anodic, pren_fail


def _crevice_score(el: ServiceElement) -> tuple:
    geo_class = JOINT_GEO.get(el.joint_type, "tight")
    gf = GEO[geo_class]

    mat = el.material_a
    cct_val = CCT.get(mat)
    cct_min = CCT_MIN.get(el.location_tag, 10)

    if cct_val is not None:
        margin = cct_val - cct_min
        cct_score = (
            0
            if margin >= 20
            else 0.2
            if margin >= 10
            else 0.5
            if margin >= 0
            else 0.8
            if margin >= -10
            else 1.0
        )
        cct_ok = margin >= 0
    else:
        cct_score = 0.3
        cct_ok = True

    sev = CC_SEV.get(el.location_tag, 0.5)
    score = min(0.35 * gf + 0.40 * cct_score + 0.25 * sev, 1.0)

    return round(score, 4), _crevice_band(score), geo_class, cct_ok


def _mitigation(g_band, g_gap, c_band, c_geo, mat, env) -> str:
    overall = max(g_band, c_band, key=_band_int)
    if overall == "LOW":
        return "None required — log in asset register"
    if overall == "CRITICAL":
        if c_geo == "critical":
            return "CRITICAL: Redesign joint geometry + material grade upgrade mandatory"
        return "CRITICAL: Full material substitution or isolation system — consult corrosion specialist"
    if c_geo in ("tight", "critical") and env in ("coastal", "swimming_pool", "marine_splash"):
        rec = "duplex 2205" if env in ("coastal", "swimming_pool") else "super-duplex 2507"
        return f"Upgrade to {rec} + specify full-face PTFE gasket or plastic-lined support"
    if g_gap and g_gap > 0.3:
        return "Specify PTFE isolation sleeve + neoprene washer at all contact points"
    return "Specify isolation gasket; ensure positive drainage; add to inspection schedule"


def _action(band):
    return {
        "LOW": "Log — include in corrosion asset register, no immediate action",
        "MEDIUM": "Flag — specify mitigation on next drawing issue; raise RFI",
        "HIGH": "BLOCK — BCF issued; lead engineer to confirm resolution before next model issue",
        "CRITICAL": "BLOCK — compliance failure; notify client; redesign or substitution mandatory",
    }[band]


def run_compliance_checks(elements: list[ServiceElement]) -> list[dict]:
    """
    Runs both GC-001 and CC-001 on every service element.
    Returns a list of result dicts ready for the dashboard, BCF, and asset register.
    """
    results = []

    for el in elements:
        g_score, g_band, g_gap, g_thr, anodic, pren_fail = _galvanic_score(el)
        c_score, c_band, c_geo, cct_ok = _crevice_score(el)

        overall_score = max(g_score, c_score)
        g_int, c_int = _band_int(g_band), _band_int(c_band)
        overall_band = g_band if g_int >= c_int else c_band
        dominant = "galvanic" if g_int >= c_int else "crevice"

        mit = _mitigation(g_band, g_gap, c_band, c_geo, el.material_a, el.location_tag)

        results.append(
            {
                # Identity
                "guid": el.guid,
                "name": el.name,
                "ifc_type": el.ifc_type,
                "description": el.description,
                "floor": el.floor,
                "system": el.system,
                "position": el.position,
                "length_m": el.length_m,
                # Materials
                "material_a": el.material_a,
                "material_b": el.material_b,
                "anodic_material": anodic,
                "environment": el.location_tag,
                "joint_type": el.joint_type,
                # Galvanic
                "galvanic_score": g_score,
                "galvanic_band": g_band,
                "voltage_gap_V": round(g_gap, 4),
                "voltage_threshold": g_thr,
                "pren_fail": pren_fail,
                # Crevice
                "crevice_score": c_score,
                "crevice_band": c_band,
                "crevice_geometry": c_geo,
                "cct_adequate": cct_ok,
                # Overall
                "overall_score": round(overall_score, 4),
                "overall_band": overall_band,
                "dominant_mechanism": dominant,
                "action": _action(overall_band),
                "mitigation": mit,
            }
        )

    return results
