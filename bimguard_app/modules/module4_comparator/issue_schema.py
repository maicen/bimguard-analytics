"""
app/modules/issue_schema.py

Data contract between Module4 (comparators) and Module5 (reporter).

An Issue represents a single compliance finding — one element that fails
one rule. Comparators in Module4 produce list[Issue]. Module5 consumes
list[Issue] to produce BCF 2.1 output, dashboard summaries, and PDF reports.

The Issue schema is deliberately mechanism-agnostic. Every compliance
domain (galvanic, crevice, clearance, centre-to-centre, seismic, fire,
accessibility) produces the same shape, differentiated only by the
`mechanism` string and mechanism-specific values in `metadata`.

UI consumption: the frontend component brief (docs/app-interior-design.md)
defines the exact same structure in TypeScript-like notation. Keep the
two in sync.
"""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Literal, Optional

SCHEMA_VERSION = "1.0.0"


# ---------------------------------------------------------------------------
# Risk banding
# ---------------------------------------------------------------------------


class RiskBand(str, Enum):
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


IssueStatus = Literal["open", "assigned", "in_review", "closed"]


# ---------------------------------------------------------------------------
# Issue dataclass
# ---------------------------------------------------------------------------


@dataclass
class Issue:
    """
    A single compliance finding.

    Produced by a Module4 comparator, consumed by Module5 and the UI.
    """

    # --- Identity ---
    id: str  # human-readable, e.g. "BGR-0007"
    element_id: str  # FK to PipingElement.id (IFC GUID)
    rule_id: str  # FK to rules table, or rule ref like "GC-001.03"

    # --- Summary ---
    title: str  # short headline shown in lists
    description: Optional[str] = None  # longer prose description

    # --- Classification ---
    band: RiskBand = RiskBand.LOW
    score: float = 0.0  # 0.0 – 1.0 composite
    mechanism: str = ""  # "GC-001 galvanic", "CC-001 crevice", …

    # --- Remediation guidance ---
    mitigation: str = ""  # recommended remediation
    assignee_role: str = "Unassigned"  # "Mechanical engineer", "Fire engineer", …

    # --- Workflow state ---
    status: IssueStatus = "open"
    created_at: str = ""  # ISO 8601 UTC
    updated_at: str = ""  # ISO 8601 UTC

    # --- Mechanism-specific extras ---
    # For galvanic: {"anode_material": "GalvanisedSteel", "cathode_material": "SS316",
    #                "voltage_v": 0.74, "area_ratio": 0.02, "pren": 25.2, ...}
    # For crevice: {"joint_type": "JT-004", "cct_required_c": 35, "cct_material_c": 10, ...}
    # Rule of thumb: put anything here that a reviewer would want to see in the
    # issue detail panel but that doesn't fit a top-level field.
    metadata: dict = field(default_factory=dict)

    # --- Standards citation (for White Box Architecture audit trail) ---
    # List of standards / threshold sources that determined this issue.
    # Each entry is a dict with at least {"standard": str, "clause": str}.
    # Example: [{"standard": "NASA-STD-6012", "clause": "Table 2",
    #            "reason": "voltage threshold 0.25V in normal environment"}]
    citations: list[dict] = field(default_factory=list)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def now_iso() -> str:
    """UTC timestamp in ISO 8601 (trailing Z), second precision."""
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def band_from_score(
    score: float,
    thresholds: dict[str, float],
) -> RiskBand:
    """
    Map a composite score (0.0–1.0) to a risk band using rulepack thresholds.

    `thresholds` expects keys "medium", "high", "critical" with the LOWER
    bound of each band. Low is everything below `thresholds["medium"]`.

    Example: {"medium": 0.35, "high": 0.65, "critical": 0.85} gives:
        score < 0.35  → LOW
        0.35 ≤ score < 0.65  → MEDIUM
        0.65 ≤ score < 0.85  → HIGH
        score ≥ 0.85  → CRITICAL
    """
    if score >= thresholds["critical"]:
        return RiskBand.CRITICAL
    if score >= thresholds["high"]:
        return RiskBand.HIGH
    if score >= thresholds["medium"]:
        return RiskBand.MEDIUM
    return RiskBand.LOW


def make_issue(
    *,
    id: str,
    element_id: str,
    rule_id: str,
    title: str,
    mechanism: str,
    band: RiskBand,
    score: float,
    mitigation: str,
    assignee_role: str = "Mechanical engineer",
    description: Optional[str] = None,
    metadata: Optional[dict] = None,
    citations: Optional[list[dict]] = None,
) -> Issue:
    """
    Factory for a new Issue with workflow defaults populated.

    Comparators use this instead of constructing Issue directly to ensure
    timestamps and status are consistently set.
    """
    ts = now_iso()
    return Issue(
        id=id,
        element_id=element_id,
        rule_id=rule_id,
        title=title,
        description=description,
        band=band,
        score=round(score, 3),  # numeric display precision
        mechanism=mechanism,
        mitigation=mitigation,
        assignee_role=assignee_role,
        status="open",
        created_at=ts,
        updated_at=ts,
        metadata=metadata or {},
        citations=citations or [],
    )


def to_dict(issue: Issue) -> dict[str, Any]:
    """JSON-serialisable dict."""
    return asdict(issue)


def to_json(issue: Issue, indent: Optional[int] = 2) -> str:
    return json.dumps(
        to_dict(issue),
        indent=indent,
        default=lambda o: o.value if isinstance(o, Enum) else str(o),
    )


def summarise(issues: list[Issue]) -> dict[str, int]:
    """Count issues by band. Used for dashboard summaries and status bars."""
    counts = {band.value: 0 for band in RiskBand}
    for issue in issues:
        counts[issue.band.value] += 1
    counts["total"] = len(issues)
    return counts


# ---------------------------------------------------------------------------
# Smoke test
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    example = make_issue(
        id="BGR-0007",
        element_id="3Kf7q8XzR1pP2mN4gV8xQ",
        rule_id="GC-001.03",
        title="Dissimilar metal coupling — galvanised steel to SS316",
        mechanism="GC-001 galvanic",
        band=RiskBand.CRITICAL,
        score=0.89,
        mitigation="Insert dielectric union between dissimilar materials.",
        metadata={
            "anode_material": "GalvanisedSteel",
            "cathode_material": "SS316",
            "voltage_v": 0.74,
            "area_ratio": 0.02,
            "environment_class": "T3_chloride",
        },
        citations=[
            {
                "standard": "NASA-STD-6012",
                "clause": "Table 2",
                "reason": "voltage gap 0.74V exceeds 0.15V threshold for harsh environment",
            },
            {
                "standard": "EN 1993-1-4",
                "clause": "§A.4",
                "reason": "guidance on dissimilar metal connections",
            },
        ],
    )
    print(f"issue_schema.py v{SCHEMA_VERSION} — example validates")
    print(to_json(example))

    summary = summarise([example])
    print(f"Summary: {summary}")
