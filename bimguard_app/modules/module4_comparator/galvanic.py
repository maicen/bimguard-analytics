"""
app/modules/comparators/galvanic.py

GC-001 galvanic corrosion comparator.

Iterates joined pairs of piping elements, identifies dissimilar-metal
couplings, and emits Issues for couplings that exceed the voltage
threshold for their environment class, weighted by anode-to-cathode
area ratio and environment severity.

This module is the port of the original bimguard_corrosion_engine.py
into the Module4 comparator architecture. The logic is unchanged; only
the input/output contracts are adapted to the repo's schema.

INPUT
    elements   — list[PipingElement] from Module2
    rule_pack  — dict loaded from the rules SQLite table (or a JSON file
                 during development). Expected keys documented below.

OUTPUT
    list[Issue] — one Issue per non-compliant element pair, at Medium
                  band or above. Compliant pairs produce no Issue.

COMPOSITE SCORE
    score = 0.50·voltage_risk + 0.30·area_ratio_risk + 0.20·environment_multiplier

    Weights are configurable via rule_pack["weights"] but these defaults
    are the ones validated against NASA-STD-6012 and WorldStainless data.

RULE PACK SHAPE (expected JSON from rule_pack["parameters"])
    galvanic_series: dict mapping canonical material key → potential (V)
    environment_voltage_thresholds: dict mapping EnvironmentClass.value →
        {max_safe_voltage_v: float, severity_multiplier: float}
    area_ratio_bands: list of {max_ratio, risk_value} ordered by max_ratio
    weights: {voltage: 0.50, area_ratio: 0.30, environment: 0.20}
    risk_band_thresholds: {medium: 0.35, high: 0.65, critical: 0.85}
    mitigations: dict mapping band → default mitigation text
    pren_by_material: dict mapping stainless key → PREN value
    pren_minimum_by_environment: dict mapping EnvironmentClass.value → min PREN

STANDARDS CITED (set in rule_pack["metadata"]["standards"])
    NASA-STD-6012 — voltage thresholds
    EN 1993-1-4 — structural stainless steel guidance
    IMOA Design Manual — PREN formula and grade selection
    Prosoco Tech Note 104 — area ratio analysis
    BS 8539 — bi-metallic assembly in construction

WHITE BOX AUDIT TRAIL
    Every Issue produced carries citations[] showing which standard and
    which threshold caused the flag. A reviewer can trace the exact
    reason without inspecting the comparator code.
"""

from __future__ import annotations

from typing import Optional

from .issue_schema import (
    Issue,
    RiskBand,
    band_from_score,
    make_issue,
)
from ..module2_ifc_read.piping_schema import (
    CANONICAL_MATERIALS,
    EnvironmentClass,
    PipingElement,
)

MECHANISM = "GC-001 galvanic"
RULE_REF_PREFIX = "GC-001"


# ---------------------------------------------------------------------------
# Public entry point
# ---------------------------------------------------------------------------


def compare(
    elements: list[PipingElement],
    rule_pack: dict,
) -> list[Issue]:
    """
    Run GC-001 galvanic compliance against a list of piping elements.

    Returns issues for every dissimilar-metal pair that exceeds the Medium
    threshold. Pairs of same-material elements produce no Issue. Elements
    with Unknown material produce one data-quality Issue each.
    """
    params = rule_pack.get("parameters", {})
    required_keys = {
        "galvanic_series",
        "environment_voltage_thresholds",
        "area_ratio_bands",
        "weights",
        "risk_band_thresholds",
    }
    missing = required_keys - params.keys()
    if missing:
        raise ValueError(f"Galvanic rule pack is missing required keys: {sorted(missing)}")

    issues: list[Issue] = []
    element_by_id = {e.id: e for e in elements}
    seen_pairs: set[tuple[str, str]] = set()
    issue_counter = [0]

    # Data quality sweep — flag Unknown materials once per element
    for element in elements:
        if element.material not in CANONICAL_MATERIALS or element.material == "Unknown":
            issues.append(_data_quality_issue(element, issue_counter))

    # Pair sweep — find dissimilar metal couplings
    for element in elements:
        for neighbour_id in element.joined_to:
            neighbour = element_by_id.get(neighbour_id)
            if neighbour is None:
                continue

            pair_key = tuple(sorted([element.id, neighbour.id]))
            if pair_key in seen_pairs:
                continue
            seen_pairs.add(pair_key)

            # Skip if either material is Unknown (already flagged above)
            if element.material == "Unknown" or neighbour.material == "Unknown":
                continue

            # Skip same-material pairs
            if element.material == neighbour.material:
                continue

            result = _assess_pair(element, neighbour, params)
            if result is None:
                continue  # below medium threshold — compliant

            issues.append(
                _build_pair_issue(
                    anode=result["anode"],
                    cathode=result["cathode"],
                    score=result["score"],
                    band=result["band"],
                    voltage_v=result["voltage_v"],
                    area_ratio=result["area_ratio"],
                    environment_class=result["environment_class"],
                    voltage_risk=result["voltage_risk"],
                    area_ratio_risk=result["area_ratio_risk"],
                    environment_multiplier=result["environment_multiplier"],
                    mitigation=_mitigation_for_band(result["band"], params),
                    citations=result["citations"],
                    rule_pack=rule_pack,
                    issue_counter=issue_counter,
                )
            )

    # PREN adequacy sweep — stainless steels in aggressive environments
    for element in elements:
        pren_issue = _assess_pren_adequacy(element, params, issue_counter, rule_pack)
        if pren_issue is not None:
            issues.append(pren_issue)

    return issues


# ---------------------------------------------------------------------------
# Pair assessment — the core GC-001 logic
# ---------------------------------------------------------------------------


def _assess_pair(
    element_a: PipingElement,
    element_b: PipingElement,
    params: dict,
) -> Optional[dict]:
    """
    Assess a dissimilar-metal pair. Returns a result dict if Medium+, else None.
    """
    series: dict[str, float] = params["galvanic_series"]
    env_thresholds: dict = params["environment_voltage_thresholds"]
    area_bands: list = params["area_ratio_bands"]
    weights: dict = params["weights"]
    thresholds: dict = params["risk_band_thresholds"]

    v_a = series.get(element_a.material)
    v_b = series.get(element_b.material)
    if v_a is None or v_b is None:
        # Material normalised but not in series table — treat as data quality
        return None

    # Identify anode (more negative) and cathode (less negative)
    if v_a < v_b:
        anode, cathode = element_a, element_b
        voltage_v = abs(v_b - v_a)
    else:
        anode, cathode = element_b, element_a
        voltage_v = abs(v_a - v_b)

    # Environment — take the more severe of the two spaces
    environment_class = _resolve_environment(anode, cathode)
    env_bucket = env_thresholds.get(
        environment_class.value,
        env_thresholds.get(EnvironmentClass.UNCLASSIFIED.value),
    )
    if env_bucket is None:
        return None

    max_safe_voltage = float(env_bucket["max_safe_voltage_v"])
    env_multiplier = float(env_bucket["severity_multiplier"])

    # Component risks — each normalised to 0.0–1.0
    voltage_risk = min(voltage_v / max_safe_voltage, 1.0) if max_safe_voltage > 0 else 1.0
    area_ratio = _compute_area_ratio(anode, cathode)
    area_ratio_risk = _area_ratio_risk_from_bands(area_ratio, area_bands)

    # Composite
    score = (
        weights["voltage"] * voltage_risk
        + weights["area_ratio"] * area_ratio_risk
        + weights["environment"] * env_multiplier
    )
    score = min(score, 1.0)

    band = band_from_score(score, thresholds)
    if band == RiskBand.LOW:
        return None  # compliant, no issue raised

    return {
        "anode": anode,
        "cathode": cathode,
        "voltage_v": voltage_v,
        "area_ratio": area_ratio,
        "environment_class": environment_class.value,
        "voltage_risk": voltage_risk,
        "area_ratio_risk": area_ratio_risk,
        "environment_multiplier": env_multiplier,
        "score": score,
        "band": band,
        "citations": [
            {
                "standard": "NASA-STD-6012",
                "clause": "Table 2 voltage thresholds",
                "reason": (
                    f"voltage gap {voltage_v:.2f}V against {max_safe_voltage:.2f}V "
                    f"max for environment {environment_class.value}"
                ),
            },
            {
                "standard": "BS 8539",
                "clause": "bi-metallic assembly",
                "reason": "guidance on dissimilar metal connections",
            },
        ],
    }


def _resolve_environment(a: PipingElement, b: PipingElement) -> EnvironmentClass:
    """Take the more severe environment of a pair."""
    severity_order = [
        EnvironmentClass.UNCLASSIFIED,
        EnvironmentClass.T0_DRY,
        EnvironmentClass.T1_INDOOR_DAMP,
        EnvironmentClass.T2_HUMID,
        EnvironmentClass.T3_CHLORIDE,
        EnvironmentClass.T5_INDUSTRIAL,
        EnvironmentClass.T4_MARINE,
    ]
    idx_a = severity_order.index(a.environment_class)
    idx_b = severity_order.index(b.environment_class)
    return severity_order[max(idx_a, idx_b)]


def _compute_area_ratio(anode: PipingElement, cathode: PipingElement) -> float:
    """
    Anode-to-cathode surface area ratio.

    A small anode connected to a large cathode is the dangerous case (the
    anode corrodes rapidly). Ratio → 0 is worst. Ratio ≥ 1 is safer.
    When surface area data is missing, fall back to a neutral 1.0.
    """
    a_area = anode.wetted_surface_area_m2 or anode.exposed_surface_area_m2
    c_area = cathode.wetted_surface_area_m2 or cathode.exposed_surface_area_m2
    if a_area is None or c_area is None or c_area == 0:
        return 1.0
    return a_area / c_area


def _area_ratio_risk_from_bands(ratio: float, bands: list[dict]) -> float:
    """
    Map a numeric area ratio to a 0.0–1.0 risk via rulepack bands.

    `bands` is a list ordered by ascending max_ratio, each with a
    risk_value. Example:
        [{"max_ratio": 0.05, "risk_value": 1.00},   # tiny anode — very bad
         {"max_ratio": 0.20, "risk_value": 0.75},
         {"max_ratio": 0.50, "risk_value": 0.50},
         {"max_ratio": 1.00, "risk_value": 0.25},
         {"max_ratio": 999,  "risk_value": 0.10}]   # cathode smaller than anode — safe
    """
    for band in bands:
        if ratio <= band["max_ratio"]:
            return float(band["risk_value"])
    return float(bands[-1]["risk_value"])


# ---------------------------------------------------------------------------
# PREN adequacy — secondary galvanic check for stainless steels
# ---------------------------------------------------------------------------


def _assess_pren_adequacy(
    element: PipingElement,
    params: dict,
    issue_counter: list,
    rule_pack: dict,
) -> Optional[Issue]:
    """
    Emit an Issue if a stainless steel element has insufficient PREN for
    its environment. Separate from galvanic pair analysis — a lone SS316
    pipe in a chloride environment can still fail this even without a
    dissimilar coupling.
    """
    pren_by_material: dict = params.get("pren_by_material", {})
    pren_min_by_env: dict = params.get("pren_minimum_by_environment", {})
    thresholds: dict = params["risk_band_thresholds"]

    pren = element.pren or pren_by_material.get(element.material)
    if pren is None:
        return None  # not a stainless with known PREN, skip silently

    min_required = pren_min_by_env.get(element.environment_class.value)
    if min_required is None:
        return None

    if pren >= min_required:
        return None  # compliant

    # Shortfall maps linearly to score above Medium
    shortfall = (min_required - pren) / min_required
    score = min(0.40 + shortfall, 1.0)
    band = band_from_score(score, thresholds)

    issue_counter[0] += 1
    return make_issue(
        id=f"BGR-{issue_counter[0]:04d}",
        element_id=element.id,
        rule_id=f"{RULE_REF_PREFIX}.PREN",
        title=(
            f"PREN {pren:.1f} below {min_required:.1f} required "
            f"for {element.environment_class.value}"
        ),
        mechanism=MECHANISM,
        band=band,
        score=score,
        mitigation=(
            f"Upgrade to a stainless grade with PREN ≥ {min_required:.0f} "
            f"(e.g. Duplex 2205 PREN 35, Super Duplex 2507 PREN 42)."
        ),
        metadata={
            "material": element.material,
            "pren": pren,
            "pren_required": min_required,
            "environment_class": element.environment_class.value,
            "check": "pren_adequacy",
        },
        citations=[
            {
                "standard": "IMOA Design Manual 4th Edition",
                "clause": "grade selection by environment",
                "reason": f"PREN {pren:.1f} < {min_required:.1f} minimum",
            },
        ],
    )


# ---------------------------------------------------------------------------
# Issue construction helpers
# ---------------------------------------------------------------------------


def _build_pair_issue(
    *,
    anode: PipingElement,
    cathode: PipingElement,
    score: float,
    band: RiskBand,
    voltage_v: float,
    area_ratio: float,
    environment_class: str,
    voltage_risk: float,
    area_ratio_risk: float,
    environment_multiplier: float,
    mitigation: str,
    citations: list,
    rule_pack: dict,
    issue_counter: list,
) -> Issue:
    issue_counter[0] += 1
    return make_issue(
        id=f"BGR-{issue_counter[0]:04d}",
        element_id=anode.id,  # issue attaches to the anode (the part that corrodes)
        rule_id=f"{RULE_REF_PREFIX}.PAIR",
        title=(f"Dissimilar metal coupling — {anode.material} anode to {cathode.material} cathode"),
        description=(
            f"Element {anode.name or anode.id[:8]} ({anode.material}) is "
            f"galvanically coupled to {cathode.name or cathode.id[:8]} "
            f"({cathode.material}) in {environment_class} environment. "
            f"Voltage gap {voltage_v:.2f}V, area ratio {area_ratio:.3f}."
        ),
        mechanism=MECHANISM,
        band=band,
        score=score,
        mitigation=mitigation,
        assignee_role="Mechanical engineer",
        metadata={
            "anode_material": anode.material,
            "cathode_material": cathode.material,
            "anode_id": anode.id,
            "cathode_id": cathode.id,
            "voltage_v": round(voltage_v, 3),
            "area_ratio": round(area_ratio, 4),
            "environment_class": environment_class,
            "voltage_risk": round(voltage_risk, 3),
            "area_ratio_risk": round(area_ratio_risk, 3),
            "environment_multiplier": round(environment_multiplier, 3),
            "check": "dissimilar_metal_pair",
            "rule_pack_version": rule_pack.get("version"),
        },
        citations=citations,
    )


def _data_quality_issue(element: PipingElement, issue_counter: list) -> Issue:
    issue_counter[0] += 1
    return make_issue(
        id=f"BGR-{issue_counter[0]:04d}",
        element_id=element.id,
        rule_id=f"{RULE_REF_PREFIX}.DATA",
        title=f"Material could not be identified on {element.name or element.id[:8]}",
        mechanism="data_quality",
        band=RiskBand.LOW,
        score=0.10,
        mitigation=(
            "Review IFC source and correct the material assignment. "
            "Galvanic compliance cannot be evaluated for this element "
            "until the material is identified."
        ),
        assignee_role="BIM coordinator",
        metadata={
            "material_raw": element.material_raw,
            "ifc_class": element.ifc_class,
            "check": "material_normalisation",
        },
    )


def _mitigation_for_band(band: RiskBand, params: dict) -> str:
    catalogue: dict = params.get("mitigations", {})
    return catalogue.get(band.value, _default_mitigation(band))


def _default_mitigation(band: RiskBand) -> str:
    if band == RiskBand.CRITICAL:
        return (
            "Insert a dielectric union or equivalent electrical isolation "
            "between the dissimilar metals, or upgrade both elements to a "
            "compatible material. Immediate action required before commissioning."
        )
    if band == RiskBand.HIGH:
        return (
            "Insert an insulating flange kit between the dissimilar metals "
            "and review coating condition. Schedule inspection within 12 months."
        )
    return (
        "Document the dissimilar coupling in the maintenance register. "
        "Inspect annually and apply protective coating at next overhaul."
    )


# ---------------------------------------------------------------------------
# Smoke test
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    import json as _json
    import sys
    from pathlib import Path

    # Allow running standalone from the comparators directory
    here = Path(__file__).resolve().parent
    sys.path.insert(0, str(here.parent.parent.parent))

    from app.modules.module2_ifc_read.piping_schema import (  # noqa: E402
        example_pump,
        example_ss316_pipe_in_plant_room,
        example_valve,
    )

    # Load example rule pack
    rule_pack_path = here / "rule_pack_galvanic_v1.json"
    with open(rule_pack_path) as f:
        rule_pack = _json.load(f)

    # Build a tiny scenario: SS316 pipe ↔ galvanised riser ↔ SS304 pump
    pipe = example_ss316_pipe_in_plant_room()
    valve = example_valve()
    pump = example_pump()
    pump.material = "GalvanisedSteel"  # force a dissimilar coupling for the demo
    pump.joined_to = [pipe.id]
    pipe.joined_to = [valve.id, pump.id]
    valve.joined_to = [pipe.id]

    results = compare([pipe, valve, pump], rule_pack)
    print(f"GC-001 comparator — {len(results)} issue(s) raised")
    for issue in results:
        print(f"  [{issue.band.value.upper()}] {issue.id}: {issue.title} (score {issue.score})")
