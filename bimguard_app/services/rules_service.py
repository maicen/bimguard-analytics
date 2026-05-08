"""Rule persistence service for CRUD, lookup, and ruleset import operations."""

import json

from app.services.persistence import PersistenceService
from app.utils import now_iso_utc, rows_desc_by_id

# ── Schema columns ────────────────────────────────────────────────────────────

_RICH_COLUMNS = {
    "source_text": str,
    "property_set": str,
    "property_name": str,
    "fallback_property": str,
    "operator": str,
    "check_value": str,  # JSON-encoded scalar / null
    "value_min": str,
    "value_max": str,
    "unit": str,
    "applies_when": str,  # JSON object string
    "severity": str,
    "keyword": str,
    "compliance_type": str,
    "exceptions": str,  # JSON array string
    "related_refs": str,  # JSON array string
    "overridden_by": str,
    "confidence": str,
    "extraction_method": str,
    "needs_review": int,
}

# Columns that classify a rule within the broader multi-mechanism schema.
# Added via required_columns so existing DBs migrate automatically.
_META_COLUMNS = {
    "mechanism": str,  # "OBC" | "GC-001" | "CC-001" | "MC-001"
    "ruleset_id": str,  # "OBC-PART9" | "BIMGUARD-GC-001" | …
    "rule_category": str,  # "property_check" | "threshold_band" | "material_property"
    # | "scoring_model" | "mitigation" | "reference_config"
}

# ── Valid controlled vocabulary ───────────────────────────────────────────────

MECHANISMS = {"OBC", "GC-001", "CC-001", "MC-001", "IFC"}

RULE_CATEGORIES = {
    "property_check",  # IFC element property assertion (OBC, building code)
    "scoring_model",  # Composite score formula + weights
    "threshold_band",  # Classification band with risk score
    "material_property",  # Material-level data (galvanic potential, CCT, MIC susceptibility)
    "reference_config",  # Named lookup entry (environment class, joint type, etc.)
    "mitigation",  # Remediation action catalogue entry
}

THEMES = {"Architecture", "MEP"}

_MEP_IFC_PREFIXES = (
    "IfcFlow",
    "IfcPipe",
    "IfcDuct",
    "IfcCable",
    "IfcDistribution",
    "IfcPump",
    "IfcBoiler",
    "IfcChiller",
    "IfcUnitary",
    "IfcSanitary",
)


class RuleService:
    """
    Encapsulates CRUD + query operations for compliance rules.

    The single 'rules' table stores all rule types across mechanisms:
    - OBC property checks (property_check)
    - Engine lookup tables (threshold_band, reference_config, material_property)
    - Scoring formulae (scoring_model)
    - Mitigation catalogue (mitigation)
    """

    def __init__(self):
        """Initialize the rules table with required schema columns."""
        all_required = {**_RICH_COLUMNS, **_META_COLUMNS}
        self._rules = PersistenceService.get_table(
            "rules",
            {
                "id": int,
                "reference": str,
                "rule_type": str,
                "description": str,
                "target_ifc_class": str,
                "parameters": str,  # kept for backward-compat / engine data
                "created_at": str,
                "updated_at": str,
            },
            required_columns=all_required,
        )

    # ── Web CRUD ──────────────────────────────────────────────────────────────

    def list_rules(self) -> list[dict]:
        """Return all rules ordered by newest first."""
        return rows_desc_by_id(self._rules)

    def get_rule(self, rule_id: int) -> dict | None:
        """Return a single rule by primary key."""
        return self._rules.get(rule_id)

    def create_rule(
        self,
        reference: str,
        rule_type: str,
        description: str,
        target_ifc_class: str,
        parameters: str = "{}",
        # rich schema
        source_text: str = "",
        property_set: str = "",
        property_name: str = "",
        fallback_property: str = "",
        operator: str = "",
        check_value=None,
        value_min=None,
        value_max=None,
        unit: str = "",
        applies_when: dict | None = None,
        severity: str = "mandatory",
        keyword: str = "",
        compliance_type: str = "",
        exceptions: list | None = None,
        related_refs: list | None = None,
        overridden_by: str = "",
        confidence: float | None = None,
        extraction_method: str = "manual",
        needs_review: bool = False,
        # classification meta
        mechanism: str = "",
        ruleset_id: str = "",
        rule_category: str = "property_check",
    ):
        """Insert a rule row into the rules table."""
        now = now_iso_utc()
        return self._rules.insert(
            {
                "reference": reference.strip(),
                "rule_type": rule_type.strip() or "numeric_comparison",
                "description": description.strip(),
                "target_ifc_class": target_ifc_class.strip(),
                "parameters": self._norm_json(parameters),
                "source_text": source_text or "",
                "property_set": property_set or "",
                "property_name": property_name or "",
                "fallback_property": fallback_property or "",
                "operator": operator or "",
                "check_value": json.dumps(check_value),
                "value_min": json.dumps(value_min),
                "value_max": json.dumps(value_max),
                "unit": unit or "",
                "applies_when": json.dumps(applies_when or {}),
                "severity": severity or "mandatory",
                "keyword": keyword or "",
                "compliance_type": compliance_type or "",
                "exceptions": json.dumps(exceptions or []),
                "related_refs": json.dumps(related_refs or []),
                "overridden_by": overridden_by or "",
                "confidence": str(confidence) if confidence is not None else "",
                "extraction_method": extraction_method or "manual",
                "needs_review": int(needs_review),
                "mechanism": mechanism or "",
                "ruleset_id": ruleset_id or "",
                "rule_category": rule_category or "property_check",
                "created_at": now,
                "updated_at": now,
            }
        )

    def update_rule(
        self,
        rule_id: int,
        reference: str,
        rule_type: str,
        description: str,
        target_ifc_class: str,
        parameters: str = "{}",
        # identity
        mechanism: str = "",
        ruleset_id: str = "",
        rule_category: str = "",
        # ifc target
        property_set: str = "",
        property_name: str = "",
        fallback_property: str = "",
        # rule logic
        operator: str = "",
        check_value=None,
        value_min=None,
        value_max=None,
        unit: str = "",
        # classification
        severity: str = "mandatory",
        keyword: str = "",
        compliance_type: str = "",
        # content
        source_text: str = "",
        # meta
        confidence: float | None = None,
        needs_review: bool = False,
    ):
        """Update editable fields for an existing rule."""
        self._rules.update(
            updates={
                "reference": reference.strip(),
                "rule_type": rule_type.strip() or "numeric_comparison",
                "description": description.strip(),
                "target_ifc_class": target_ifc_class.strip(),
                "parameters": self._norm_json(parameters),
                "mechanism": mechanism or "",
                "ruleset_id": ruleset_id or "",
                "rule_category": rule_category or "",
                "property_set": property_set or "",
                "property_name": property_name or "",
                "fallback_property": fallback_property or "",
                "operator": operator or "",
                "check_value": json.dumps(self._parse_numeric(check_value)),
                "value_min": json.dumps(self._parse_numeric(value_min)),
                "value_max": json.dumps(self._parse_numeric(value_max)),
                "unit": unit or "",
                "severity": severity or "mandatory",
                "keyword": keyword or "",
                "compliance_type": compliance_type or "",
                "source_text": source_text or "",
                "confidence": str(confidence) if confidence is not None else "",
                "needs_review": int(bool(needs_review)),
                "updated_at": now_iso_utc(),
            },
            pk_values=rule_id,
        )

    @staticmethod
    def _parse_numeric(value):
        """Convert a form string value to float, or None if blank/invalid."""
        if value is None:
            return None
        s = str(value).strip()
        if not s:
            return None
        try:
            return float(s)
        except ValueError:
            return None

    def delete_rule(self, rule_id: int):
        """Delete a rule by primary key."""
        self._rules.delete(rule_id)

    # ── Classification queries ────────────────────────────────────────────────

    def has_ruleset(self, ruleset_id: str) -> bool:
        """Return True if at least one rule with this ruleset_id exists."""
        return len(list(self._rules.rows_where("ruleset_id = ?", [ruleset_id], limit=1))) > 0

    def list_by_mechanism(self, mechanism: str) -> list[dict]:
        """Return all rules for a corrosion or code-check mechanism."""
        return list(self._rules.rows_where("mechanism = ?", [mechanism]))

    def list_by_ruleset(self, ruleset_id: str) -> list[dict]:
        """Return all rules that belong to a ruleset identifier."""
        return list(self._rules.rows_where("ruleset_id = ?", [ruleset_id]))

    def list_by_category(self, rule_category: str) -> list[dict]:
        """Return all rules matching the provided rule category."""
        return list(self._rules.rows_where("rule_category = ?", [rule_category]))

    @staticmethod
    def normalize_theme(theme: str | None) -> str:
        """Normalize a user-selected theme to one of the supported values."""
        value = (theme or "").strip().lower()
        if value == "mep":
            return "MEP"
        return "Architecture"

    @classmethod
    def infer_theme(cls, rule: dict) -> str:
        """Infer Architecture vs MEP for a rule from mechanism and IFC target hints."""
        mechanism = (rule.get("mechanism") or "").strip().upper()
        if mechanism in {"GC-001", "CC-001", "MC-001"}:
            return "MEP"
        if mechanism in {"OBC", "IFC"}:
            return "Architecture"

        target = (rule.get("target_ifc_class") or "").strip()
        if target.startswith(_MEP_IFC_PREFIXES):
            return "MEP"

        return "Architecture"

    def list_by_theme(self, theme: str) -> list[dict]:
        """Return all rules categorized under the requested analysis theme."""
        selected = self.normalize_theme(theme)
        return [r for r in self._rules.rows if self.infer_theme(r) == selected]

    # ── Pipeline query methods (used by RuleStore adapter) ────────────────────

    def count(self) -> int:
        """Return the total number of rules in storage."""
        return len(list(self._rules.rows))

    def fetch_rules_for_target(self, target_ifc_class: str) -> list[dict]:
        """Return rules targeting a specific IFC class."""
        return list(self._rules.rows_where("target_ifc_class = ?", [target_ifc_class]))

    def fetch_mandatory_rules(self) -> list[dict]:
        """Return rules marked with mandatory severity."""
        return list(self._rules.rows_where("severity = 'mandatory'"))

    def fetch_rules_by_ref(self, ref: str) -> list[dict]:
        """Return rules whose reference contains the provided token."""
        return list(self._rules.rows_where("reference LIKE ?", [f"%{ref}%"]))

    def fetch_needs_review(self) -> list[dict]:
        """Return rules flagged for manual review."""
        return list(self._rules.rows_where("needs_review = 1"))

    def get_existing_entity_types(self) -> list[str]:
        """Return distinct target IFC classes present in stored rules."""
        seen: set[str] = set()
        result: list[str] = []
        for r in self._rules.rows:
            t = r.get("target_ifc_class") or ""
            if t and t not in seen:
                seen.add(t)
                result.append(t)
        return result

    def get_rules_sample(self, limit: int = 3) -> list[dict]:
        """Return a small sample of mandatory rules for previews."""
        return list(self._rules.rows_where("severity = 'mandatory'", limit=limit))

    def summary(self) -> dict:
        """Return aggregate counts of rules by entity, source, and mechanism."""
        rules = list(self._rules.rows)
        by_entity: dict[str, int] = {}
        by_source: dict[str, int] = {}
        by_mechanism: dict[str, int] = {}
        mandatory_count = 0
        for r in rules:
            target = r.get("target_ifc_class") or ""
            by_entity[target] = by_entity.get(target, 0) + 1
            source = r.get("extraction_method") or ""
            by_source[source] = by_source.get(source, 0) + 1
            mech = r.get("mechanism") or "—"
            by_mechanism[mech] = by_mechanism.get(mech, 0) + 1
            if r.get("severity") == "mandatory":
                mandatory_count += 1
        return {
            "total": len(rules),
            "mandatory_count": mandatory_count,
            "by_entity": by_entity,
            "by_source": by_source,
            "by_mechanism": by_mechanism,
        }

    # ── JSON ruleset import ───────────────────────────────────────────────────

    def import_ruleset(self, json_data: dict) -> int:
        """
        Import rules from a canonical JSON ruleset document.

        Expected format:
            {
                "ruleset_id": "MY-RULESET",
                "mechanism":  "GC-001",          # optional
                "rules": [
                    {
                        "ref":           "R-001",
                        "rule_type":     "numeric_comparison",
                        "rule_category": "property_check",
                        "desc":          "...",
                        "target":        "IfcDoor",
                        ...
                    }
                ]
            }

        Field names follow the CLI convention (ref/desc/target) OR the web
        convention (reference/description/target_ifc_class) — both accepted.
        Returns the number of rules successfully imported.
        """
        ruleset_id = str(json_data.get("ruleset_id") or "").strip()
        if not ruleset_id:
            raise ValueError("JSON ruleset must have a non-empty 'ruleset_id'.")

        rules = json_data.get("rules")
        if not isinstance(rules, list):
            raise ValueError("JSON ruleset must have a 'rules' array.")

        top_mechanism = str(json_data.get("mechanism") or "")
        saved = 0
        for rule in rules:
            if not isinstance(rule, dict):
                continue
            desc = str(rule.get("desc") or rule.get("description") or "").strip()
            if not desc:
                continue
            self.create_rule(
                reference=str(rule.get("ref") or rule.get("reference") or "").strip(),
                rule_type=str(rule.get("rule_type") or "numeric_comparison"),
                description=desc,
                target_ifc_class=str(
                    rule.get("target") or rule.get("target_ifc_class") or "Unspecified"
                ).strip(),
                source_text=str(rule.get("source_text") or ""),
                property_set=str(rule.get("property_set") or ""),
                property_name=str(rule.get("property_name") or ""),
                fallback_property=str(rule.get("fallback_property") or ""),
                operator=str(rule.get("operator") or ""),
                check_value=(
                    rule.get("check_value") if "check_value" in rule else rule.get("value")
                ),
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
                confidence=(
                    float(rule["confidence"]) if rule.get("confidence") is not None else None
                ),
                extraction_method=str(rule.get("extraction_method") or "import"),
                needs_review=bool(rule.get("needs_review", False)),
                mechanism=str(rule.get("mechanism") or top_mechanism),
                ruleset_id=ruleset_id,
                rule_category=str(rule.get("rule_category") or "property_check"),
                parameters=json.dumps(rule.get("parameters") or {}),
            )
            saved += 1
        return saved

    # ── Helpers ───────────────────────────────────────────────────────────────

    def _norm_json(self, value: str) -> str:
        """Normalize JSON strings to a compact canonical representation."""
        raw = (value or "").strip()
        if not raw:
            return "{}"
        try:
            return json.dumps(json.loads(raw), separators=(",", ":"))
        except json.JSONDecodeError:
            return raw
