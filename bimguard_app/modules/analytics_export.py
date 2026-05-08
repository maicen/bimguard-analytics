"""
BIMGUARD AI — Analytics Export Module
=====================================
Module:   modules/analytics_export.py
Version:  1.0.0
Produces: Power BI-ready CSV export pack conforming to the BIMGUARD Analytics Data Contract v1.0

Output files (written to analytics_export/ subfolder):
    facts/
        issues.csv              — Fact table. One row per compliance issue.
        issue_status_history.csv — Bridge table. One row per status change event.

    dimensions/
        dim_projects.csv        — Project dimension
        dim_models.csv          — BIM model / IFC file dimension
        dim_rules.csv           — Compliance rule dimension (GC-001, CC-001, …)
        dim_locations.csv       — Spatial location dimension (floor + zone)
        dim_assignments.csv     — Engineer / assignee dimension
        dim_issue_types.csv     — Issue type dimension
        dim_severity.csv        — Severity / risk band dimension
        dim_status.csv          — Workflow status dimension
        dim_mechanism.csv       — Corrosion mechanism dimension

    meta/
        export_manifest.json    — Timestamp, row counts, schema version, run metadata

Usage from app.py or compliance_runner:
    from modules.analytics_export import AnalyticsExporter
    exporter = AnalyticsExporter(results, project_meta)
    export_path = exporter.export(output_dir="analytics_export")
    print(f"Export written to {export_path}")

    results:      list[dict] — unified output from compliance_runner.run_all()
    project_meta: dict       — project-level metadata (name, ifc_path, run_id, etc.)
"""

import csv
import json
import os
import uuid
from datetime import datetime, date, timedelta
from pathlib import Path
from typing import Any


# ---------------------------------------------------------------------------
# Constants — canonical lookup tables
# These must be kept in sync with bimguard_corrosion_engine.py and
# bimguard_crevice_engine.py so that IDs match the compliance engine outputs.
# ---------------------------------------------------------------------------

SEVERITY_CATALOGUE = [
    {
        "SeverityID": "SEV-LOW",
        "SeverityName": "Low",
        "SeverityCode": "L",
        "RiskBand": "Low",
        "ScoreMin": 0.00,
        "ScoreMax": 0.34,
        "Colour": "#4CAF50",
        "BCFPriority": 3,
        "SortOrder": 1,
    },
    {
        "SeverityID": "SEV-MED",
        "SeverityName": "Medium",
        "SeverityCode": "M",
        "RiskBand": "Medium",
        "ScoreMin": 0.35,
        "ScoreMax": 0.64,
        "Colour": "#FFC107",
        "BCFPriority": 2,
        "SortOrder": 2,
    },
    {
        "SeverityID": "SEV-HIGH",
        "SeverityName": "High",
        "SeverityCode": "H",
        "RiskBand": "High",
        "ScoreMin": 0.65,
        "ScoreMax": 0.84,
        "Colour": "#FF5722",
        "BCFPriority": 1,
        "SortOrder": 3,
    },
    {
        "SeverityID": "SEV-CRIT",
        "SeverityName": "Critical",
        "SeverityCode": "C",
        "RiskBand": "Critical",
        "ScoreMin": 0.85,
        "ScoreMax": 1.00,
        "Colour": "#B71C1C",
        "BCFPriority": 0,
        "SortOrder": 4,
    },
]

STATUS_CATALOGUE = [
    {
        "StatusID": "STS-OPEN",
        "StatusName": "Open",
        "StatusCode": "OPEN",
        "IsActive": True,
        "IsTerminal": False,
        "SortOrder": 1,
    },
    {
        "StatusID": "STS-PROG",
        "StatusName": "In Progress",
        "StatusCode": "IN_PROG",
        "IsActive": True,
        "IsTerminal": False,
        "SortOrder": 2,
    },
    {
        "StatusID": "STS-REVW",
        "StatusName": "In Review",
        "StatusCode": "IN_REVW",
        "IsActive": True,
        "IsTerminal": False,
        "SortOrder": 3,
    },
    {
        "StatusID": "STS-CLOS",
        "StatusName": "Closed",
        "StatusCode": "CLOSED",
        "IsActive": False,
        "IsTerminal": True,
        "SortOrder": 4,
    },
    {
        "StatusID": "STS-APPR",
        "StatusName": "Approved",
        "StatusCode": "APPROVED",
        "IsActive": False,
        "IsTerminal": True,
        "SortOrder": 5,
    },
    {
        "StatusID": "STS-VOID",
        "StatusName": "Voided",
        "StatusCode": "VOIDED",
        "IsActive": False,
        "IsTerminal": True,
        "SortOrder": 6,
    },
]

RULE_CATALOGUE = [
    {
        "RuleID": "RULE-GC001",
        "RuleCode": "GC-001",
        "RuleName": "Galvanic Corrosion Risk",
        "MechanismID": "MECH-GAL",
        "Standard": "NASA-STD-6012 / WorldStainless",
        "Version": "1.0.0",
        "IsActive": True,
        "Description": (
            "Checks voltage gap between dissimilar metals, area ratio, "
            "environment class, and PREN adequacy for stainless steels."
        ),
    },
    {
        "RuleID": "RULE-CC001",
        "RuleCode": "CC-001",
        "RuleName": "Crevice Corrosion Risk",
        "MechanismID": "MECH-CRV",
        "Standard": "EN ISO 15329 / ASTM G48 Method B / CIRIA C692",
        "Version": "1.0.0",
        "IsActive": True,
        "Description": (
            "Checks joint geometry class, Critical Crevice Corrosion Temperature "
            "(CCT), and environment severity classification."
        ),
    },
    {
        "RuleID": "RULE-MC001",
        "RuleCode": "MC-001",
        "RuleName": "Microbially Influenced Corrosion Risk",
        "MechanismID": "MECH-MIC",
        "Standard": "CIBSE Guide G / ASHRAE 188",
        "Version": "0.1.0-draft",
        "IsActive": False,
        "Description": (
            "Planned module: checks dead-leg pipework, stagnant water zones, "
            "and under-insulation scenarios. Not yet released."
        ),
    },
]

MECHANISM_CATALOGUE = [
    {
        "MechanismID": "MECH-GAL",
        "MechanismName": "Galvanic",
        "MechanismFullName": "Galvanic Corrosion",
        "EngineCode": "GC-001",
        "IsImplemented": True,
    },
    {
        "MechanismID": "MECH-CRV",
        "MechanismName": "Crevice",
        "MechanismFullName": "Crevice Corrosion",
        "EngineCode": "CC-001",
        "IsImplemented": True,
    },
    {
        "MechanismID": "MECH-MIC",
        "MechanismName": "MIC",
        "MechanismFullName": "Microbially Influenced Corrosion",
        "EngineCode": "MC-001",
        "IsImplemented": False,
    },
]

ISSUE_TYPE_CATALOGUE = [
    {
        "IssueTypeID": "IT-COR",
        "IssueTypeName": "Corrosion Risk",
        "IssueTypeCode": "CORROSION",
        "Category": "Compliance",
    },
    {
        "IssueTypeID": "IT-MAT",
        "IssueTypeName": "Material Incompatibility",
        "IssueTypeCode": "MATERIAL",
        "Category": "Compliance",
    },
    {
        "IssueTypeID": "IT-ENV",
        "IssueTypeName": "Environment Class Mismatch",
        "IssueTypeCode": "ENVIRONMENT",
        "Category": "Compliance",
    },
    {
        "IssueTypeID": "IT-GEO",
        "IssueTypeName": "Joint Geometry Risk",
        "IssueTypeCode": "GEOMETRY",
        "Category": "Compliance",
    },
    {
        "IssueTypeID": "IT-DEV",
        "IssueTypeName": "Point Cloud Deviation",
        "IssueTypeCode": "DEVIATION",
        "Category": "Survey",
    },
]

# Score → SeverityID lookup (must mirror SEVERITY_CATALOGUE bands)
def _score_to_severity_id(score: float) -> str:
    if score >= 0.85:
        return "SEV-CRIT"
    elif score >= 0.65:
        return "SEV-HIGH"
    elif score >= 0.35:
        return "SEV-MED"
    else:
        return "SEV-LOW"


# ---------------------------------------------------------------------------
# AnalyticsExporter
# ---------------------------------------------------------------------------

class AnalyticsExporter:
    """
    Transforms BIMGUARD AI compliance results into a Power BI-ready CSV pack.

    Parameters
    ----------
    results : list[dict]
        Unified output from compliance_runner.run_all().
        Each dict must contain at minimum:
            element_id, element_type, material_primary, material_secondary,
            floor, zone, system_type, environment_class,
            galvanic_score, crevice_score, combined_score,
            joint_type, assignee, ifc_guid, x, y, z,
            cost_impact_gbp, delay_days, mitigation
        Fields that are missing will be filled with sensible defaults.

    project_meta : dict
        Project-level context:
            project_id    (str, optional) — auto-generated if absent
            project_name  (str)
            project_code  (str, optional)
            ifc_path      (str)
            ifc_schema    (str, e.g. "IFC4", "IFC2X3")
            run_id        (str, optional) — auto-generated if absent
            run_by        (str, optional)
            baseline_date (str ISO8601, optional) — programme start date
    """

    SCHEMA_VERSION = "1.0.0"

    def __init__(self, results: list[dict], project_meta: dict):
        self.results = results
        self.meta = project_meta
        self.run_id = project_meta.get("run_id") or f"RUN-{uuid.uuid4().hex[:8].upper()}"
        self.project_id = project_meta.get("project_id") or f"PROJ-{uuid.uuid4().hex[:6].upper()}"
        self.run_timestamp = datetime.utcnow()
        self._location_registry: dict[str, str] = {}   # (floor, zone) → LocationID
        self._assignee_registry: dict[str, str] = {}   # name → AssigneeID
        self._model_registry: dict[str, str] = {}      # ifc_path → ModelID

    # ------------------------------------------------------------------
    # Public entry point
    # ------------------------------------------------------------------

    def export(self, output_dir: str = "analytics_export") -> str:
        """
        Run the full export pipeline and write all CSVs.

        Returns the absolute path to the output directory.
        """
        base = Path(output_dir)
        facts_dir = base / "facts"
        dims_dir = base / "dimensions"
        meta_dir = base / "meta"
        for d in (facts_dir, dims_dir, meta_dir):
            d.mkdir(parents=True, exist_ok=True)

        # --- Build dimension registries first (needed by fact rows) --------
        locations = self._build_locations()
        assignees = self._build_assignees()
        models = self._build_models()

        # --- Write dimension tables ----------------------------------------
        self._write_csv(dims_dir / "dim_projects.csv", self._dim_projects())
        self._write_csv(dims_dir / "dim_models.csv", models)
        self._write_csv(dims_dir / "dim_rules.csv", RULE_CATALOGUE)
        self._write_csv(dims_dir / "dim_locations.csv", locations)
        self._write_csv(dims_dir / "dim_assignments.csv", assignees)
        self._write_csv(dims_dir / "dim_issue_types.csv", ISSUE_TYPE_CATALOGUE)
        self._write_csv(dims_dir / "dim_severity.csv", SEVERITY_CATALOGUE)
        self._write_csv(dims_dir / "dim_status.csv", STATUS_CATALOGUE)
        self._write_csv(dims_dir / "dim_mechanism.csv", MECHANISM_CATALOGUE)

        # --- Build and write fact tables ------------------------------------
        issues, history = self._build_issues_and_history()
        self._write_csv(facts_dir / "issues.csv", issues)
        self._write_csv(facts_dir / "issue_status_history.csv", history)

        # --- Write manifest ------------------------------------------------
        manifest = self._build_manifest(issues, history, locations, assignees, models)
        with open(meta_dir / "export_manifest.json", "w", encoding="utf-8") as f:
            json.dump(manifest, f, indent=2, default=str)

        return str(base.resolve())

    # ------------------------------------------------------------------
    # Dimension builders
    # ------------------------------------------------------------------

    def _dim_projects(self) -> list[dict]:
        return [
            {
                "ProjectID": self.project_id,
                "ProjectName": self.meta.get("project_name", "BIMGUARD Project"),
                "ProjectCode": self.meta.get("project_code", "BGP-001"),
                "Client": self.meta.get("client", ""),
                "Sector": self.meta.get("sector", ""),
                "Country": self.meta.get("country", ""),
                "Currency": self.meta.get("currency", "GBP"),
                "BaselineDate": self.meta.get("baseline_date", ""),
                "IsActive": True,
                "CreatedDate": self.run_timestamp.date().isoformat(),
            }
        ]

    def _build_models(self) -> list[dict]:
        """Derive one model row per unique IFC path in the results."""
        seen: dict[str, dict] = {}
        ifc_path = self.meta.get("ifc_path", "unknown.ifc")
        model_id = f"MDL-{uuid.uuid4().hex[:6].upper()}"
        self._model_registry[ifc_path] = model_id
        seen[ifc_path] = {
            "ModelID": model_id,
            "ProjectID": self.project_id,
            "ModelName": Path(ifc_path).stem if ifc_path != "unknown.ifc" else "Demo Model",
            "IFCPath": ifc_path,
            "IFCSchema": self.meta.get("ifc_schema", "IFC4"),
            "Discipline": self.meta.get("discipline", "MEP"),
            "AuthoringTool": self.meta.get("authoring_tool", ""),
            "ExportDate": self.run_timestamp.date().isoformat(),
            "ElementCount": len(self.results),
        }
        return list(seen.values())

    def _build_locations(self) -> list[dict]:
        """Derive unique (floor, zone) combinations from results."""
        rows = []
        seen = set()
        for r in self.results:
            floor = str(r.get("floor", "Unknown Floor")).strip() or "Unknown Floor"
            zone = str(r.get("zone", "General")).strip() or "General"
            key = (floor, zone)
            if key not in seen:
                seen.add(key)
                loc_id = f"LOC-{len(rows) + 1:04d}"
                self._location_registry[key] = loc_id
                rows.append(
                    {
                        "LocationID": loc_id,
                        "ProjectID": self.project_id,
                        "Floor": floor,
                        "Zone": zone,
                        "Level": self._extract_level_number(floor),
                        "Building": self.meta.get("building", ""),
                        "Wing": self.meta.get("wing", ""),
                        "Description": f"{floor} — {zone}",
                    }
                )
        if not rows:
            # Fallback if results are empty
            loc_id = "LOC-0001"
            self._location_registry[("Ground Floor", "General")] = loc_id
            rows.append(
                {
                    "LocationID": loc_id,
                    "ProjectID": self.project_id,
                    "Floor": "Ground Floor",
                    "Zone": "General",
                    "Level": 0,
                    "Building": "",
                    "Wing": "",
                    "Description": "Ground Floor — General",
                }
            )
        return rows

    def _build_assignees(self) -> list[dict]:
        """Derive unique assignees from results plus a default unassigned entry."""
        rows = []
        seen = set()

        # Always include Unassigned
        unassigned_id = "ASN-UNASSIGNED"
        self._assignee_registry["Unassigned"] = unassigned_id
        rows.append(
            {
                "AssigneeID": unassigned_id,
                "Name": "Unassigned",
                "Discipline": "",
                "Role": "",
                "Email": "",
                "IsActive": True,
                "ProjectID": self.project_id,
            }
        )
        seen.add("Unassigned")

        for r in self.results:
            name = str(r.get("assignee", "Unassigned")).strip() or "Unassigned"
            if name not in seen:
                seen.add(name)
                asn_id = f"ASN-{len(rows):04d}"
                self._assignee_registry[name] = asn_id
                rows.append(
                    {
                        "AssigneeID": asn_id,
                        "Name": name,
                        "Discipline": self._infer_discipline(name),
                        "Role": "Service Engineer",
                        "Email": "",
                        "IsActive": True,
                        "ProjectID": self.project_id,
                    }
                )
        return rows

    # ------------------------------------------------------------------
    # Fact builders
    # ------------------------------------------------------------------

    def _build_issues_and_history(self) -> tuple[list[dict], list[dict]]:
        """
        Build the issues fact table and the issue_status_history bridge table.

        Every issue starts as Open. For demonstration and programme integration,
        previously-run results can carry a status field — if present it is used,
        otherwise all issues are Open on first export.
        """
        issues = []
        history = []

        ifc_path = self.meta.get("ifc_path", "unknown.ifc")
        model_id = self._model_registry.get(ifc_path, "MDL-0001")

        for idx, r in enumerate(self.results):
            # --- Resolve keys ---------------------------------------------
            element_id = str(r.get("element_id", f"ELEM-{idx + 1:04d}"))
            ifc_guid = str(r.get("ifc_guid", str(uuid.uuid4())))
            issue_id = f"ISS-{self.run_id}-{idx + 1:04d}"

            galvanic_score = float(r.get("galvanic_score", 0.0))
            crevice_score = float(r.get("crevice_score", 0.0))
            combined_score = float(r.get("combined_score", max(galvanic_score, crevice_score)))

            severity_id = _score_to_severity_id(combined_score)

            floor = str(r.get("floor", "Unknown Floor")).strip() or "Unknown Floor"
            zone = str(r.get("zone", "General")).strip() or "General"
            location_id = self._location_registry.get((floor, zone), "LOC-0001")

            assignee_name = str(r.get("assignee", "Unassigned")).strip() or "Unassigned"
            assignee_id = self._assignee_registry.get(assignee_name, "ASN-UNASSIGNED")

            # Determine rule and mechanism
            dominant_mechanism = self._dominant_mechanism(galvanic_score, crevice_score)
            rule_id = "RULE-GC001" if dominant_mechanism == "Galvanic" else "RULE-CC001"

            # Issue type
            issue_type_id = self._infer_issue_type(r, galvanic_score, crevice_score)

            # Status — use existing status if result carries one, else Open
            raw_status = str(r.get("status", "Open")).strip()
            status_id = self._normalise_status(raw_status)

            created_date = self.run_timestamp.date().isoformat()
            closed_date = r.get("closed_date", "")

            # Cost and schedule
            cost_impact = float(r.get("cost_impact_gbp", 0.0))
            delay_days = int(r.get("delay_days", 0))

            # Coordinates
            x = float(r.get("x", 0.0))
            y = float(r.get("y", 0.0))
            z = float(r.get("z", 0.0))

            # BCF
            bcf_guid = str(r.get("bcf_guid", ifc_guid))

            issue_row = {
                # --- Surrogate and foreign keys ---
                "IssueID": issue_id,
                "ProjectID": self.project_id,
                "ModelID": model_id,
                "RuleID": rule_id,
                "LocationID": location_id,
                "AssigneeID": assignee_id,
                "SeverityID": severity_id,
                "StatusID": status_id,
                "IssueTypeID": issue_type_id,
                # --- IFC / BCF identity ---
                "IFCGUID": ifc_guid,
                "BCFGuid": bcf_guid,
                "ElementID": element_id,
                "ElementType": str(r.get("element_type", "")),
                # --- Materials ---
                "MaterialPrimary": str(r.get("material_primary", "")),
                "MaterialSecondary": str(r.get("material_secondary", "")),
                "JointType": str(r.get("joint_type", "")),
                # --- Environment ---
                "EnvironmentClass": str(r.get("environment_class", "")),
                "SystemType": str(r.get("system_type", "")),
                # --- Scores ---
                "GalvanicScore": round(galvanic_score, 4),
                "CreviceScore": round(crevice_score, 4),
                "CombinedScore": round(combined_score, 4),
                "DominantMechanism": dominant_mechanism,
                # --- Spatial ---
                "X": round(x, 3),
                "Y": round(y, 3),
                "Z": round(z, 3),
                # --- Programme ---
                "CostImpactGBP": round(cost_impact, 2),
                "DelayDays": delay_days,
                # --- Mitigation ---
                "Mitigation": str(r.get("mitigation", "")),
                "Notes": str(r.get("notes", "")),
                # --- Dates ---
                "CreatedDate": created_date,
                "ClosedDate": closed_date if closed_date else "",
                "RunID": self.run_id,
                # --- Derived booleans for easy DAX filtering ---
                "IsOpen": status_id in ("STS-OPEN", "STS-PROG", "STS-REVW"),
                "IsCriticalOrHigh": severity_id in ("SEV-CRIT", "SEV-HIGH"),
                "IsComplianceFailure": combined_score >= 0.35,
            }
            issues.append(issue_row)

            # --- Status history: one creation event per issue --------------
            history.append(
                self._history_row(
                    issue_id=issue_id,
                    from_status_id="",           # no prior status — this is the creation event
                    to_status_id="STS-OPEN",
                    changed_date=self.run_timestamp.isoformat(),
                    changed_by=self.meta.get("run_by", "BIMGUARD AI"),
                    comment=f"Issue raised automatically by {rule_id} compliance check.",
                    event_type="Created",
                )
            )

            # If result already carries a non-Open status, add a transition event
            if status_id != "STS-OPEN":
                history.append(
                    self._history_row(
                        issue_id=issue_id,
                        from_status_id="STS-OPEN",
                        to_status_id=status_id,
                        changed_date=closed_date if closed_date else self.run_timestamp.isoformat(),
                        changed_by=assignee_name,
                        comment="Status updated.",
                        event_type="StatusChange",
                    )
                )

        return issues, history

    # ------------------------------------------------------------------
    # Helper methods
    # ------------------------------------------------------------------

    @staticmethod
    def _history_row(
        issue_id: str,
        from_status_id: str,
        to_status_id: str,
        changed_date: str,
        changed_by: str,
        comment: str,
        event_type: str,
    ) -> dict:
        return {
            "HistoryID": f"HIST-{uuid.uuid4().hex[:10].upper()}",
            "IssueID": issue_id,
            "FromStatusID": from_status_id,
            "ToStatusID": to_status_id,
            "ChangedDate": changed_date,
            "ChangedBy": changed_by,
            "Comment": comment,
            "EventType": event_type,
        }

    @staticmethod
    def _dominant_mechanism(galvanic: float, crevice: float) -> str:
        if galvanic == 0.0 and crevice == 0.0:
            return "Unknown"
        return "Galvanic" if galvanic >= crevice else "Crevice"

    @staticmethod
    def _infer_issue_type(r: dict, galvanic: float, crevice: float) -> str:
        """Choose the most descriptive issue type based on available data."""
        if r.get("joint_type"):
            return "IT-GEO"
        if galvanic > 0.0 and crevice == 0.0:
            return "IT-MAT"
        if crevice > 0.0:
            return "IT-GEO"
        env = str(r.get("environment_class", ""))
        if env and env not in ("C1", "T0"):
            return "IT-ENV"
        return "IT-COR"

    @staticmethod
    def _normalise_status(raw: str) -> str:
        mapping = {
            "open": "STS-OPEN",
            "in progress": "STS-PROG",
            "in_progress": "STS-PROG",
            "in review": "STS-REVW",
            "in_review": "STS-REVW",
            "closed": "STS-CLOS",
            "approved": "STS-APPR",
            "voided": "STS-VOID",
        }
        return mapping.get(raw.lower(), "STS-OPEN")

    @staticmethod
    def _infer_discipline(name: str) -> str:
        name_lower = name.lower()
        if any(k in name_lower for k in ("mech", "hvac", "pip")):
            return "Mechanical"
        if any(k in name_lower for k in ("elec", "electrical")):
            return "Electrical"
        if any(k in name_lower for k in ("struct", "civil")):
            return "Structural"
        if any(k in name_lower for k in ("plumb", "drain")):
            return "Plumbing"
        return "MEP"

    @staticmethod
    def _extract_level_number(floor_name: str) -> int:
        """Attempt to extract a numeric level from a floor name string."""
        import re
        match = re.search(r"[-]?\d+", floor_name)
        if match:
            return int(match.group())
        lower = floor_name.lower()
        if "ground" in lower or "g" == lower:
            return 0
        if "basement" in lower or "b" in lower:
            return -1
        if "roof" in lower or "plant" in lower:
            return 99
        return 0

    @staticmethod
    def _write_csv(path: Path, rows: list[dict]) -> None:
        if not rows:
            return
        with open(path, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
            writer.writeheader()
            writer.writerows(rows)

    def _build_manifest(
        self,
        issues: list[dict],
        history: list[dict],
        locations: list[dict],
        assignees: list[dict],
        models: list[dict],
    ) -> dict:
        severity_counts = {}
        for row in issues:
            sev = row["SeverityID"]
            severity_counts[sev] = severity_counts.get(sev, 0) + 1

        return {
            "schema_version": self.SCHEMA_VERSION,
            "run_id": self.run_id,
            "project_id": self.project_id,
            "project_name": self.meta.get("project_name", ""),
            "export_timestamp_utc": self.run_timestamp.isoformat(),
            "exported_by": self.meta.get("run_by", "BIMGUARD AI"),
            "ifc_path": self.meta.get("ifc_path", ""),
            "ifc_schema": self.meta.get("ifc_schema", ""),
            "row_counts": {
                "issues": len(issues),
                "issue_status_history": len(history),
                "dim_projects": 1,
                "dim_models": len(models),
                "dim_rules": len(RULE_CATALOGUE),
                "dim_locations": len(locations),
                "dim_assignments": len(assignees),
                "dim_issue_types": len(ISSUE_TYPE_CATALOGUE),
                "dim_severity": len(SEVERITY_CATALOGUE),
                "dim_status": len(STATUS_CATALOGUE),
                "dim_mechanism": len(MECHANISM_CATALOGUE),
            },
            "severity_summary": severity_counts,
            "cost_impact_total_gbp": round(
                sum(r["CostImpactGBP"] for r in issues), 2
            ),
            "total_delay_days": sum(r["DelayDays"] for r in issues),
            "open_issues": sum(1 for r in issues if r["IsOpen"]),
            "critical_or_high_issues": sum(1 for r in issues if r["IsCriticalOrHigh"]),
            "compliance_failures": sum(1 for r in issues if r["IsComplianceFailure"]),
        }


# ---------------------------------------------------------------------------
# Streamlit integration helper
# ---------------------------------------------------------------------------

def run_export_from_streamlit(
    compliance_results: list[dict],
    project_name: str,
    ifc_path: str,
    output_dir: str = "analytics_export",
    **kwargs,
) -> dict:
    """
    Convenience wrapper for calling from app.py or compliance_runner.

    Returns the manifest dict so Streamlit can display a summary.

    Example usage in app.py:
        from modules.analytics_export import run_export_from_streamlit
        manifest = run_export_from_streamlit(
            compliance_results=st.session_state["results"],
            project_name="Heathrow T2B",
            ifc_path=uploaded_ifc.name,
            output_dir="analytics_export",
            run_by="engineer@example.com",
            baseline_date="2025-01-06",
        )
        st.success(f"Export complete — {manifest['row_counts']['issues']} issues written.")
    """
    project_meta = {
        "project_name": project_name,
        "ifc_path": ifc_path,
        **kwargs,
    }
    exporter = AnalyticsExporter(compliance_results, project_meta)
    export_path = exporter.export(output_dir=output_dir)

    manifest_path = Path(export_path) / "meta" / "export_manifest.json"
    with open(manifest_path, encoding="utf-8") as f:
        manifest = json.load(f)

    manifest["export_path"] = export_path
    return manifest


# ---------------------------------------------------------------------------
# CLI entry point — useful for testing outside Streamlit
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    """
    Quick smoke test with synthetic results.
    Run with:  python modules/analytics_export.py
    """
    import random

    MATERIALS = [
        ("Carbon Steel", "Copper"),
        ("SS316", "Carbon Steel"),
        ("Galvanised Steel", "Copper"),
        ("SS304", "SS316"),
        ("Copper", "Aluminium"),
    ]
    JOINT_TYPES = ["flanged_joint", "threaded_joint", "welded_joint", "compression_fitting"]
    FLOORS = ["Basement B1", "Ground Floor", "Level 1", "Level 2", "Level 3", "Roof Plant"]
    ZONES = ["Plant Room", "Riser", "Ceiling Void", "Pool Hall", "Kitchen", "General"]
    ASSIGNEES = [
        "Mechanical Engineer",
        "Plumbing Engineer",
        "Structural Engineer",
        "Unassigned",
    ]
    ENV_CLASSES = ["C1", "C2", "C3", "C4", "T2", "T3", "T4"]

    random.seed(42)
    synthetic_results = []
    for i in range(25):
        mat = random.choice(MATERIALS)
        gal = round(random.uniform(0.0, 1.0), 4)
        crv = round(random.uniform(0.0, 1.0), 4)
        combined = round(max(gal, crv) * 0.7 + min(gal, crv) * 0.3, 4)
        synthetic_results.append(
            {
                "element_id": f"ELEM-{i + 1:04d}",
                "element_type": random.choice(["IfcPipeSegment", "IfcPipeFitting", "IfcFlowTerminal"]),
                "ifc_guid": str(uuid.uuid4()),
                "material_primary": mat[0],
                "material_secondary": mat[1],
                "floor": random.choice(FLOORS),
                "zone": random.choice(ZONES),
                "system_type": random.choice(["CHW", "HWS", "CWS", "LTHW", "Drainage"]),
                "environment_class": random.choice(ENV_CLASSES),
                "joint_type": random.choice(JOINT_TYPES),
                "galvanic_score": gal,
                "crevice_score": crv,
                "combined_score": combined,
                "assignee": random.choice(ASSIGNEES),
                "cost_impact_gbp": round(combined * random.uniform(2000, 15000), 2),
                "delay_days": int(combined * random.uniform(5, 30)),
                "mitigation": "Review material specification and apply isolation flange.",
                "x": round(random.uniform(0, 50), 3),
                "y": round(random.uniform(0, 30), 3),
                "z": round(random.uniform(0, 20), 3),
            }
        )

    project_meta = {
        "project_name": "BIMGUARD Demo Project",
        "project_code": "BGP-DEMO",
        "ifc_path": "demo_building.ifc",
        "ifc_schema": "IFC4",
        "client": "Demo Client Ltd",
        "sector": "Commercial",
        "country": "UK",
        "currency": "GBP",
        "baseline_date": "2025-01-06",
        "run_by": "BIMGUARD AI Demo",
    }

    exporter = AnalyticsExporter(synthetic_results, project_meta)
    path = exporter.export("analytics_export_test")

    manifest_path = Path(path) / "meta" / "export_manifest.json"
    with open(manifest_path) as f:
        m = json.load(f)

    print("\n✓ BIMGUARD AI — Analytics Export Complete")
    print(f"  Output directory : {path}")
    print(f"  Run ID           : {m['run_id']}")
    print(f"  Issues exported  : {m['row_counts']['issues']}")
    print(f"  History rows     : {m['row_counts']['issue_status_history']}")
    print(f"  Total cost impact: £{m['cost_impact_total_gbp']:,.2f}")
    print(f"  Total delay      : {m['total_delay_days']} working days")
    print(f"  Severity summary : {m['severity_summary']}")
    print()
    print("  Files written:")
    for folder in ("facts", "dimensions", "meta"):
        folder_path = Path(path) / folder
        for f_path in sorted(folder_path.iterdir()):
            size = f_path.stat().st_size
            print(f"    {folder}/{f_path.name}  ({size:,} bytes)")
