"""
module3_rule_builder/rule_store.py
-----------------------------------
Adapter that forwards all reads/writes to the web app's RuleService so the
CLI pipeline and the web app share one SQLite table (data/bimguard.sqlite).

Public interface is identical to the original standalone RuleStore, so
RuleGenerator, TableRuleBuilder, RuleConverter, obc_seed_rules, orchestrator,
and enhanced_orchestrator need no changes.

Field-name mapping (CLI → web):
    ref    → reference
    desc   → description
    target → target_ifc_class

The db_path constructor argument is accepted but ignored; the connection is
managed by PersistenceService.
"""

import json

try:
    from app.services.rules_service import RuleService
except ImportError:
    # Running as a bare CLI script from app/modules/ — adjust sys.path first
    import sys
    from pathlib import Path

    sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))
    from app.services.rules_service import RuleService


def _jload(value):
    """Safely deserialize a JSON string stored in the web DB."""
    if value is None or value == "" or value == "null":
        return None
    try:
        return json.loads(value)
    except (json.JSONDecodeError, TypeError):
        return value


def _to_cli(r: dict) -> dict:
    """Convert a web-format rule row to the CLI field-name convention."""
    return {
        "ref": r.get("reference", ""),
        "desc": r.get("description", ""),
        "target": r.get("target_ifc_class", ""),
        "rule_type": r.get("rule_type", ""),
        "source_text": r.get("source_text", ""),
        "property_set": r.get("property_set", ""),
        "property_name": r.get("property_name", ""),
        "fallback_property": r.get("fallback_property", ""),
        "operator": r.get("operator", ""),
        "check_value": _jload(r.get("check_value")),
        "value_min": _jload(r.get("value_min")),
        "value_max": _jload(r.get("value_max")),
        "unit": r.get("unit", ""),
        "applies_when": _jload(r.get("applies_when")) or {},
        "severity": r.get("severity", "mandatory"),
        "keyword": r.get("keyword", ""),
        "compliance_type": r.get("compliance_type", ""),
        "exceptions": _jload(r.get("exceptions")) or [],
        "related_refs": _jload(r.get("related_refs")) or [],
        "overridden_by": r.get("overridden_by", ""),
        "confidence": float(r.get("confidence") or 0.8),
        "extraction_method": r.get("extraction_method", "llm"),
        "needs_review": bool(r.get("needs_review", 0)),
        # keep the web PK available for callers that need it
        "id": r.get("id"),
    }


class RuleStore:
    """
    Drop-in replacement for the original standalone RuleStore.
    Delegates all persistence to RuleService (shared web app table).
    """

    def __init__(self, db_path=None):
        # db_path accepted for backward compat but ignored — PersistenceService
        # owns the connection.
        self._svc = RuleService()
        print(f"[RuleStore] Connected — {self.count()} existing rules")

    # ── WRITE ─────────────────────────────────────────────────────────────────

    def save_rule(self, rule: dict) -> str:
        """
        Save a single validated rule dict.  Returns the new row ID as str.
        Accepts the CLI field-name convention (ref / desc / target).
        """
        row = self._svc.create_rule(
            reference=str(rule.get("ref") or ""),
            rule_type=str(rule.get("rule_type") or "numeric_comparison"),
            description=str(rule.get("desc") or ""),
            target_ifc_class=str(rule.get("target") or "Unspecified"),
            source_text=str(rule.get("source_text") or ""),
            property_set=str(rule.get("property_set") or ""),
            property_name=str(rule.get("property_name") or ""),
            fallback_property=str(rule.get("fallback_property") or ""),
            operator=str(rule.get("operator") or ""),
            check_value=rule.get("check_value"),
            value_min=rule.get("value_min"),
            value_max=rule.get("value_max"),
            unit=str(rule.get("unit") or ""),
            applies_when=rule.get("applies_when") or {},
            severity=str(rule.get("severity") or "mandatory"),
            keyword=str(rule.get("keyword") or ""),
            compliance_type=str(rule.get("compliance_type") or ""),
            exceptions=rule.get("exceptions") or [],
            related_refs=rule.get("related_refs") or [],
            overridden_by=str(rule.get("overridden_by") or ""),
            confidence=float(rule.get("confidence") or 0.8),
            extraction_method=str(rule.get("extraction_method") or "llm"),
            needs_review=bool(rule.get("needs_review", False)),
        )
        return str(row.id)

    def clear_all_rules(self):
        """Delete every rule from the shared table. Use in testing only."""
        for r in self._svc.list_rules():
            self._svc.delete_rule(r["id"])
        print("[RuleStore] All rules deleted")

    # ── READ ──────────────────────────────────────────────────────────────────

    def get_all_rules(self) -> list[dict]:
        return [_to_cli(r) for r in self._svc.list_rules()]

    def fetch_rules_for_target(self, target: str) -> list[dict]:
        return [_to_cli(r) for r in self._svc.fetch_rules_for_target(target)]

    def fetch_rules_for_entity(self, target: str) -> list[dict]:
        return self.fetch_rules_for_target(target)

    def fetch_mandatory_rules(self) -> list[dict]:
        return [_to_cli(r) for r in self._svc.fetch_mandatory_rules()]

    def fetch_rules_by_ref(self, ref: str) -> list[dict]:
        return [_to_cli(r) for r in self._svc.fetch_rules_by_ref(ref)]

    def fetch_needs_review(self) -> list[dict]:
        return [_to_cli(r) for r in self._svc.fetch_needs_review()]

    def get_existing_entity_types(self) -> list[str]:
        return self._svc.get_existing_entity_types()

    def get_rules_sample(self, limit: int = 3) -> list[dict]:
        return [_to_cli(r) for r in self._svc.get_rules_sample(limit)]

    def fetch_all_as_dataframe(self):
        try:
            import pandas as pd
        except ImportError:
            raise RuntimeError("pandas is required for fetch_all_as_dataframe()")
        rules = self.get_all_rules()
        if not rules:
            import pandas as pd

            return pd.DataFrame(
                columns=[
                    "ref",
                    "rule_type",
                    "target",
                    "property_name",
                    "operator",
                    "check_value",
                    "value_min",
                    "value_max",
                    "unit",
                    "severity",
                    "desc",
                ]
            )
        import pandas as pd

        return pd.DataFrame(rules)[
            [
                "ref",
                "rule_type",
                "target",
                "property_name",
                "operator",
                "check_value",
                "value_min",
                "value_max",
                "unit",
                "severity",
                "desc",
            ]
        ]

    def count(self) -> int:
        return self._svc.count()

    def summary(self) -> dict:
        return self._svc.summary()

    def close(self):
        pass  # PersistenceService owns the connection lifecycle
