"""
BIMGUARD AI — Schedule & Cost Impact Module
Links BCF corrosion issues to programme activities.
Outputs: delay days, cost impact, Gantt-ready data.
"""

import datetime

import pandas as pd

# Default cost and duration model per risk band and mechanism
# These are configurable — can be loaded from a project-specific CSV
IMPACT_MODEL = {
    "CRITICAL": {
        "galvanic": {
            "days": 14,
            "cost_gbp": 18500,
            "description": "Full redesign, material substitution, re-issue drawings",
        },
        "crevice": {
            "days": 10,
            "cost_gbp": 12000,
            "description": "Material grade upgrade, re-specify, re-issue",
        },
        "combined": {
            "days": 21,
            "cost_gbp": 25000,
            "description": "Combined galvanic + crevice redesign, specialist review",
        },
    },
    "HIGH": {
        "galvanic": {
            "days": 7,
            "cost_gbp": 6500,
            "description": "Isolation detail specified, drawing re-issue, inspection",
        },
        "crevice": {
            "days": 5,
            "cost_gbp": 4500,
            "description": "Grade upgrade specified, drawing re-issue",
        },
        "combined": {
            "days": 10,
            "cost_gbp": 9000,
            "description": "Both isolation and grade upgrade, lead engineer review",
        },
    },
    "MEDIUM": {
        "galvanic": {
            "days": 3,
            "cost_gbp": 1800,
            "description": "Isolation washer specified, RFI raised",
        },
        "crevice": {
            "days": 2,
            "cost_gbp": 1200,
            "description": "Gasket type change, specification note",
        },
        "combined": {
            "days": 4,
            "cost_gbp": 2500,
            "description": "Combined specification update, coordination review",
        },
    },
    "LOW": {
        "galvanic": {
            "days": 0,
            "cost_gbp": 0,
            "description": "Log in asset register — no programme impact",
        },
        "crevice": {
            "days": 0,
            "cost_gbp": 0,
            "description": "Log in asset register — no programme impact",
        },
        "combined": {
            "days": 0,
            "cost_gbp": 0,
            "description": "Log in asset register — no programme impact",
        },
    },
}

# MEP programme activities — generic baseline schedule
# Start dates are offsets from a project start date (configurable)
BASE_ACTIVITIES = [
    {"id": "A1", "name": "RIBA Stage 3 — Spatial Coordination", "start_offset": 0, "duration": 30},
    {"id": "A2", "name": "MEP Design Development (Stage 4)", "start_offset": 30, "duration": 45},
    {"id": "A3", "name": "Technical Design Freeze", "start_offset": 75, "duration": 10},
    {"id": "A4", "name": "Procurement — Long-Lead MEP Items", "start_offset": 85, "duration": 30},
    {
        "id": "A5",
        "name": "IFC + BCF Coordination (BIMGUARD AI)",
        "start_offset": 60,
        "duration": 20,
    },
    {"id": "A6", "name": "Issue Resolution (BCF Close-out)", "start_offset": 80, "duration": 15},
    {"id": "A7", "name": "MEP Fabrication & Prefabrication", "start_offset": 115, "duration": 40},
    {"id": "A8", "name": "MEP Installation on Site", "start_offset": 155, "duration": 60},
    {"id": "A9", "name": "Commissioning & Testing", "start_offset": 215, "duration": 30},
    {"id": "A10", "name": "Practical Completion", "start_offset": 245, "duration": 5},
]


def calculate_impact(results: list[dict], project_start: datetime.date = None) -> dict:
    """
    Calculates schedule and cost impact from compliance check results.

    Args:
        results:       List of dicts from run_compliance_checks()
        project_start: Programme start date (defaults to today)

    Returns:
        Dict with total_days, total_cost, issue_impacts, gantt_data
    """
    if project_start is None:
        project_start = datetime.date.today()

    total_days = 0
    total_cost = 0
    issue_impacts = []

    for r in results:
        band = r.get("overall_band", "LOW")
        mech = r.get("dominant_mechanism", "galvanic")
        if band not in IMPACT_MODEL:
            continue

        impact = IMPACT_MODEL[band].get(mech, IMPACT_MODEL[band]["galvanic"])
        days = impact["days"]
        cost = impact["cost_gbp"]

        total_days += days
        total_cost += cost

        issue_impacts.append(
            {
                "component": r.get("name", "Component"),
                "floor": r.get("floor", ""),
                "system": r.get("system", ""),
                "band": band,
                "mechanism": mech,
                "delay_days": days,
                "cost_gbp": cost,
                "action": impact["description"],
                "guid": r.get("guid", ""),
            }
        )

    # Build Gantt data
    gantt = _build_gantt(project_start, total_days)

    return {
        "total_delay_days": total_days,
        "total_cost_gbp": total_cost,
        "issue_impacts": issue_impacts,
        "gantt_data": gantt,
        "project_start": project_start.isoformat(),
    }


def _build_gantt(project_start: datetime.date, delay_days: int) -> list[dict]:
    """
    Builds Gantt chart data including baseline and delayed programme.
    Issues are assumed to impact the coordination and resolution activities.
    """
    rows = []
    impact_activities = {"A5", "A6", "A7", "A8", "A9", "A10"}

    for act in BASE_ACTIVITIES:
        start = project_start + datetime.timedelta(days=act["start_offset"])
        end = start + datetime.timedelta(days=act["duration"])

        # Delayed version: activities from A6 onwards are shifted
        delayed_start = start
        delayed_end = end
        if act["id"] in impact_activities and act["id"] != "A5":
            delayed_start = start + datetime.timedelta(days=delay_days)
            delayed_end = end + datetime.timedelta(days=delay_days)

        rows.append(
            {
                "Activity": act["name"],
                "ID": act["id"],
                "Baseline Start": start.isoformat(),
                "Baseline End": end.isoformat(),
                "Delayed Start": delayed_start.isoformat(),
                "Delayed End": delayed_end.isoformat(),
                "Impacted": act["id"] in impact_activities,
                "Delay Days": delay_days
                if act["id"] in impact_activities and act["id"] != "A5"
                else 0,
            }
        )

    return rows


def impact_summary_df(impact: dict) -> pd.DataFrame:
    """Returns issue impacts as a tidy pandas DataFrame."""
    return pd.DataFrame(impact["issue_impacts"])


def gantt_df(impact: dict) -> pd.DataFrame:
    """Returns Gantt data as a pandas DataFrame for Plotly rendering."""
    return pd.DataFrame(impact["gantt_data"])
