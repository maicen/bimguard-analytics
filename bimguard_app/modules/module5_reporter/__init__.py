"""
module5_reporter.py
--------------------
Generates reports from Module 4 compliance results.

Outputs:
  - CSV summary (one row per rule)
  - BCF topic dicts for failed rules (consumed by bcf_generator)
  - Visual summary dict for the web UI
"""

import csv
import io
import uuid
from datetime import datetime


class Module5_Reporter:
    """Generates compliance reports from Module 4 results."""

    # ── Public API ────────────────────────────────────────────────────────────

    def generate_csv_summary(self, compliance_results: list[dict]) -> str:
        """
        Return a CSV string — one row per rule — suitable for download.

        Columns: Rule Ref, Description, Target IFC, Property, Operator,
                 Expected, Unit, Severity, Status, Pass, Fail, Missing, Total
        """
        output = io.StringIO()
        writer = csv.writer(output)
        writer.writerow([
            "Rule Ref", "Description", "Target IFC Class",
            "Property Name", "Operator", "Expected Value", "Unit",
            "Severity", "Status",
            "Pass", "Fail", "Missing", "Total Elements",
        ])
        for r in compliance_results:
            if r.get("operator") == "between":
                expected = f"{r.get('value_min')}–{r.get('value_max')}"
            else:
                expected = str(r.get("check_value") or "")
            writer.writerow([
                r.get("rule_ref",      ""),
                r.get("rule_desc",     ""),
                r.get("target",        ""),
                r.get("property_name", ""),
                r.get("operator",      ""),
                expected,
                r.get("unit",          ""),
                r.get("severity",      ""),
                r.get("status",        ""),
                r.get("pass_count",    0),
                r.get("fail_count",    0),
                r.get("missing_count", 0),
                r.get("total_count",   0),
            ])
        return output.getvalue()

    def create_bcf_topic(self, failure: dict, rule: dict) -> dict:
        """
        Create a BCF-compatible topic dict for one element failure.

        Args:
            failure: one entry from compliance_result["failures"]
            rule:    the parent compliance result dict

        Returns:
            dict with guid, title, description, type, status, element_guid
        """
        return {
            "guid":         str(uuid.uuid4()),
            "title":        f"[{rule.get('rule_ref')}] {(rule.get('rule_desc') or '')[:80]}",
            "description":  (
                f"Element : {failure.get('element_name')}\n"
                f"Property: {rule.get('property_name')}\n"
                f"Issue   : {failure.get('reason')}"
            ),
            "type":         "Error" if rule.get("severity") == "mandatory" else "Warning",
            "status":       "Open",
            "priority":     rule.get("severity", "recommended"),
            "creation_date": datetime.utcnow().isoformat(),
            "element_guid": failure.get("guid"),
        }

    def render_visual_report(self, compliance_results: list[dict]) -> dict:
        """
        Return a summary dict for display in the web UI dashboard / analyze page.

        Returns:
            {total_rules, passed, failed, missing_data, no_elements,
             pass_rate, mandatory_failed, by_target}
        """
        total       = len(compliance_results)
        passed      = sum(1 for r in compliance_results if r.get("status") == "PASS")
        failed      = sum(1 for r in compliance_results if r.get("status") == "FAIL")
        missing     = sum(1 for r in compliance_results if r.get("status") in ("MISSING_DATA", "PARTIAL"))
        no_elem     = sum(1 for r in compliance_results if r.get("status") == "NO_ELEMENTS")
        mand_failed = sum(
            1 for r in compliance_results
            if r.get("status") == "FAIL" and r.get("severity") == "mandatory"
        )

        by_target: dict[str, dict] = {}
        for r in compliance_results:
            t = r.get("target", "Unknown")
            if t not in by_target:
                by_target[t] = {"pass": 0, "fail": 0, "other": 0}
            s = r.get("status", "")
            if s == "PASS":
                by_target[t]["pass"] += 1
            elif s == "FAIL":
                by_target[t]["fail"] += 1
            else:
                by_target[t]["other"] += 1

        return {
            "total_rules":      total,
            "passed":           passed,
            "failed":           failed,
            "missing_data":     missing,
            "no_elements":      no_elem,
            "mandatory_failed": mand_failed,
            "pass_rate":        round(100 * passed / total, 1) if total else 0,
            "by_target":        by_target,
        }

    def bcf_topics_for_results(self, compliance_results: list[dict]) -> list[dict]:
        """Convenience: generate all BCF topics for every failure in all results."""
        topics = []
        for rule in compliance_results:
            if rule.get("status") == "FAIL":
                for failure in rule.get("failures", []):
                    topics.append(self.create_bcf_topic(failure, rule))
        return topics
