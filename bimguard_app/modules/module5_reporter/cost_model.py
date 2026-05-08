"""
BIMGUARD AI — User-Configurable Cost Model
modules/cost_model.py

Replaces the hardcoded cost/duration impact model with a user-uploadable
CSV file. Falls back to built-in defaults if no CSV is uploaded.

CSV format expected (see generate_template() for headers):
  risk_band, mechanism, material, cost_per_item_gbp, duration_days,
  remediation_description, contractor_type

Usage in Streamlit:
  from modules.cost_model import CostModel
  model = CostModel()
  model.load_from_upload(uploaded_file)  # optional
  impact = model.calculate_impact(results)
"""

import csv
import io
from dataclasses import dataclass, field

import pandas as pd

# ── BUILT-IN DEFAULT RATES ────────────────────────────────────────────────────
# Based on UK commercial MEP remediation unit rates, 2025
# Mechanism codes: GC = galvanic, CC = crevice, MC = MIC
DEFAULT_RATES = [
    # risk_band, mechanism, material_group, cost_gbp, days, description, contractor
    (
        "Critical",
        "GC",
        "copper_steel",
        8500,
        5,
        "Isolate, replace dissimilar metal joint, install dielectric coupling",
        "Mechanical",
    ),
    (
        "Critical",
        "GC",
        "ss_carbon",
        9200,
        6,
        "Material substitution or full-isolation system",
        "Mechanical",
    ),
    (
        "Critical",
        "GC",
        "galv_copper",
        7800,
        4,
        "Replace galvanised fittings, install isolation gaskets",
        "Mechanical",
    ),
    (
        "Critical",
        "GC",
        "default",
        8800,
        5,
        "Galvanic isolation — material investigation required",
        "Mechanical",
    ),
    (
        "Critical",
        "CC",
        "ss304_pool",
        12400,
        8,
        "Upgrade to Duplex 2205 or Super Duplex 2507 — full joint replacement",
        "Mechanical",
    ),
    (
        "Critical",
        "CC",
        "ss316_chloride",
        10800,
        7,
        "Upgrade flange specification and gasket material",
        "Mechanical",
    ),
    (
        "Critical",
        "CC",
        "default",
        11000,
        7,
        "Crevice mitigation — material and joint geometry review",
        "Mechanical",
    ),
    (
        "Critical",
        "MC",
        "fire_supp",
        6200,
        4,
        "Flush, biocide treatment, install auto-flush device",
        "Public Health",
    ),
    (
        "Critical",
        "MC",
        "hot_water_deadleg",
        7400,
        5,
        "Eliminate dead-leg, reconfigure to through-flow",
        "Public Health",
    ),
    (
        "Critical",
        "MC",
        "default",
        7000,
        5,
        "MIC remediation — dead-leg elimination or auto-flush",
        "Public Health",
    ),
    (
        "High",
        "GC",
        "default",
        4800,
        3,
        "Galvanic isolation gaskets and non-conductive spacers",
        "Mechanical",
    ),
    (
        "High",
        "CC",
        "default",
        5600,
        4,
        "Joint specification upgrade and environment barrier",
        "Mechanical",
    ),
    (
        "High",
        "MC",
        "default",
        3800,
        3,
        "Flushing regime, monitoring programme implementation",
        "Public Health",
    ),
    (
        "Medium",
        "GC",
        "default",
        2200,
        2,
        "Protective coating and monitoring — low priority",
        "Mechanical",
    ),
    ("Medium", "CC", "default", 2800, 2, "Sealing and monitoring programme", "Mechanical"),
    (
        "Medium",
        "MC",
        "default",
        1800,
        1,
        "Microbiological monitoring and periodic flushing",
        "Public Health",
    ),
    (
        "Low",
        "GC",
        "default",
        400,
        0,
        "Record in asset register — no immediate action",
        "Mechanical",
    ),
    (
        "Low",
        "CC",
        "default",
        400,
        0,
        "Record in asset register — no immediate action",
        "Mechanical",
    ),
    ("Low", "MC", "default", 400, 0, "Record in asset register — monitoring only", "Public Health"),
]

COLUMN_HEADERS = [
    "risk_band",
    "mechanism",
    "material_group",
    "cost_per_item_gbp",
    "duration_days",
    "remediation_description",
    "contractor_type",
]


@dataclass
class ImpactSummary:
    """Aggregated cost and schedule impact across all flagged elements."""

    total_cost_gbp: float = 0.0
    total_days: int = 0
    issues_by_band: dict = field(default_factory=dict)
    issues_by_mechanism: dict = field(default_factory=dict)
    issues_by_contractor: dict = field(default_factory=dict)
    line_items: list = field(default_factory=list)


class CostModel:
    """
    Manages the cost and duration impact model for BIMGUARD AI.
    Supports both built-in default rates and user-uploaded CSV overrides.
    """

    def __init__(self):
        self._rates = self._build_default_index()
        self.source = "Built-in defaults (UK commercial MEP 2025)"
        self.is_custom = False

    def _build_default_index(self) -> dict:
        """Build lookup index from default rate table."""
        index = {}
        for row in DEFAULT_RATES:
            band, mech, mat, cost, days, desc, contractor = row
            key = (band, mech, mat)
            index[key] = {
                "cost_per_item_gbp": cost,
                "duration_days": days,
                "remediation_description": desc,
                "contractor_type": contractor,
            }
        return index

    def load_from_upload(self, uploaded_file) -> tuple[bool, str]:
        """
        Load cost rates from a user-uploaded CSV file.
        Returns (success: bool, message: str).
        Expected columns: risk_band, mechanism, material_group,
                         cost_per_item_gbp, duration_days,
                         remediation_description, contractor_type
        """
        try:
            df = pd.read_csv(uploaded_file)
            # Validate required columns
            missing = [c for c in COLUMN_HEADERS if c not in df.columns]
            if missing:
                return False, f"CSV missing required columns: {', '.join(missing)}"

            # Build new index
            new_index = {}
            for _, row in df.iterrows():
                key = (
                    str(row["risk_band"]).strip(),
                    str(row["mechanism"]).strip().upper(),
                    str(row["material_group"]).strip().lower(),
                )
                new_index[key] = {
                    "cost_per_item_gbp": float(row["cost_per_item_gbp"]),
                    "duration_days": int(row["duration_days"]),
                    "remediation_description": str(row["remediation_description"]),
                    "contractor_type": str(row["contractor_type"]),
                }

            self._rates = new_index
            self.is_custom = True
            self.source = f"User-uploaded CSV ({len(new_index)} rate entries)"
            return True, f"Cost model loaded successfully — {len(new_index)} rate entries."

        except Exception as e:
            return False, f"Failed to load CSV: {str(e)}"

    def _lookup_rate(self, risk_band: str, mechanism: str, material_key: str) -> dict:
        """
        Look up rate for a given risk band, mechanism, and material.
        Falls back through: exact match → band+mechanism default → band default.
        """
        mech = mechanism.upper()[:2]  # normalise to GC/CC/MC

        # Try exact match
        key = (risk_band, mech, material_key.lower())
        if key in self._rates:
            return self._rates[key]

        # Try band + mechanism default
        key = (risk_band, mech, "default")
        if key in self._rates:
            return self._rates[key]

        # Fallback to lowest band default
        key = ("Medium", mech, "default")
        if key in self._rates:
            return self._rates[key]

        # Last resort
        return {
            "cost_per_item_gbp": 3000,
            "duration_days": 2,
            "remediation_description": "Remediation cost estimated — rate not found in model",
            "contractor_type": "Mechanical",
        }

    def calculate_impact(self, results: list) -> ImpactSummary:
        """
        Calculate cost and schedule impact across a list of compliance results.
        Each result dict must have: risk_band, mechanism, material (optional).
        Returns an ImpactSummary dataclass.
        """
        summary = ImpactSummary()

        for r in results:
            if not isinstance(r, dict):
                # Handle dataclass results
                r = r.__dict__ if hasattr(r, "__dict__") else {}

            band = r.get("risk_band", "Medium")
            mech = r.get("mechanism", r.get("GC001_mechanism", "GC"))
            material = r.get("material", r.get("material_key", "default"))

            # Skip Low band from cost totals (record only)
            if band == "Low":
                continue

            rate = self._lookup_rate(band, mech, material)
            cost = rate["cost_per_item_gbp"]
            days = rate["duration_days"]
            desc = rate["remediation_description"]
            contractor = rate["contractor_type"]

            summary.total_cost_gbp += cost
            summary.total_days += days

            # Band breakdown
            summary.issues_by_band[band] = summary.issues_by_band.get(
                band, {"count": 0, "cost": 0.0, "days": 0}
            )
            summary.issues_by_band[band]["count"] += 1
            summary.issues_by_band[band]["cost"] += cost
            summary.issues_by_band[band]["days"] += days

            # Mechanism breakdown
            summary.issues_by_mechanism[mech] = summary.issues_by_mechanism.get(
                mech, {"count": 0, "cost": 0.0, "days": 0}
            )
            summary.issues_by_mechanism[mech]["count"] += 1
            summary.issues_by_mechanism[mech]["cost"] += cost
            summary.issues_by_mechanism[mech]["days"] += days

            # Contractor breakdown
            summary.issues_by_contractor[contractor] = summary.issues_by_contractor.get(
                contractor, {"count": 0, "cost": 0.0}
            )
            summary.issues_by_contractor[contractor]["count"] += 1
            summary.issues_by_contractor[contractor]["cost"] += cost

            # Line item
            summary.line_items.append(
                {
                    "risk_band": band,
                    "mechanism": mech,
                    "material": material,
                    "cost_gbp": cost,
                    "duration_days": days,
                    "remediation": desc,
                    "contractor": contractor,
                    "element_id": r.get("global_id", r.get("GlobalID", "Unknown")),
                }
            )

        return summary

    @staticmethod
    def generate_template() -> bytes:
        """
        Generate a blank CSV template for the user to populate.
        Returns CSV bytes for Streamlit download button.
        """
        output = io.StringIO()
        writer = csv.writer(output)
        writer.writerow(COLUMN_HEADERS)
        # Write a few example rows
        examples = [
            [
                "Critical",
                "GC",
                "copper_steel",
                9000,
                5,
                "Replace dissimilar metal joint",
                "Mechanical",
            ],
            ["Critical", "CC", "ss316_chloride", 11000, 7, "Upgrade to Duplex 2205", "Mechanical"],
            ["Critical", "MC", "hot_water_deadleg", 7500, 5, "Eliminate dead-leg", "Public Health"],
            ["High", "GC", "default", 5000, 3, "Install dielectric isolation", "Mechanical"],
            ["Medium", "MC", "default", 2000, 1, "Monitoring programme", "Public Health"],
            ["Low", "GC", "default", 400, 0, "Asset register only", "Mechanical"],
        ]
        for row in examples:
            writer.writerow(row)
        return output.getvalue().encode("utf-8")

    def to_dataframe(self) -> pd.DataFrame:
        """Return the current rate table as a Pandas DataFrame for display."""
        rows = []
        for (band, mech, mat), data in self._rates.items():
            rows.append({"risk_band": band, "mechanism": mech, "material_group": mat, **data})
        return pd.DataFrame(rows)


# ── STREAMLIT INTEGRATION SNIPPET ────────────────────────────────────────────
STREAMLIT_SNIPPET = """
# Add to your Streamlit app — Schedule & Cost Impact page
# ─────────────────────────────────────────────────────────────────────────────
import streamlit as st
from modules.cost_model import CostModel

# Initialise model (once, using session state)
if "cost_model" not in st.session_state:
    st.session_state.cost_model = CostModel()

model = st.session_state.cost_model

st.subheader("Cost model configuration")

col1, col2 = st.columns([2, 1])
with col1:
    uploaded = st.file_uploader(
        "Upload custom cost rate CSV (optional — built-in defaults used if not uploaded)",
        type=["csv"],
        help="CSV must contain: risk_band, mechanism, material_group, cost_per_item_gbp, duration_days, remediation_description, contractor_type"
    )
    if uploaded:
        success, msg = model.load_from_upload(uploaded)
        if success:
            st.success(msg)
        else:
            st.error(msg)

with col2:
    template_bytes = CostModel.generate_template()
    st.download_button(
        label="Download CSV template",
        data=template_bytes,
        file_name="bimguard_cost_model_template.csv",
        mime="text/csv"
    )

st.caption(f"Active model: {model.source}")

# Run impact calculation
if st.session_state.get("compliance_results"):
    impact = model.calculate_impact(st.session_state.compliance_results)

    # Display summary metrics
    c1, c2, c3 = st.columns(3)
    c1.metric("Total remediation cost", f"£{impact.total_cost_gbp:,.0f}")
    c2.metric("Total programme delay", f"{impact.total_days} days")
    c3.metric("Issues costed", str(len(impact.line_items)))
"""
