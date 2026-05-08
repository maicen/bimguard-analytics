"""
module3_rule_builder/rule_generator.py
----------------------------------------
Validates, enriches, and saves rules to the RuleStore.
Acts as the gatekeeper between raw LLM output and the database.

Responsibilities:
    - Auto-correct loose entity names to IFC class names
      e.g. "stair" → "IfcStairFlight"
    - Auto-fill property_set when LLM omits it
    - Validate required fields per rule type
    - Save valid rules, skip and log invalid ones
    - Handle both single rules and batches

Usage:
    from module3_rule_builder.rule_generator import RuleGenerator
    from module3_rule_builder.rule_store import RuleStore
    from config import DB_PATH

    store     = RuleStore(DB_PATH)
    generator = RuleGenerator(store)
    generator.save_batch(rules, source_doc="OBC_Part9_PDF")
"""

try:
    from config import (
        IFC_PROPERTY_SET_MAP,
        OBC_TO_IFC_MAP,
        RULE_TYPE_REQUIRED_FIELDS,
        SOURCE_DOC_PDF,
        VALID_OPERATORS,
        VALID_RULE_TYPES,
    )
except ImportError:
    from app.modules.config import (
        IFC_PROPERTY_SET_MAP,
        OBC_TO_IFC_MAP,
        RULE_TYPE_REQUIRED_FIELDS,
        SOURCE_DOC_PDF,
        VALID_OPERATORS,
        VALID_RULE_TYPES,
    )

# Fields that must always be present with non-empty values regardless of rule type
_ALWAYS_REQUIRED = ["rule_type", "target", "desc"]

# Fields not required when operator is "exists" or "not_exists"
_VALUE_OPERATORS = {"exists", "not_exists"}


class RuleGenerator:
    """
    Validates, enriches, and saves rules to the RuleStore.
    All LLM output and manual seeds pass through here before DB insertion.
    """

    def __init__(self, rule_store):
        """
        Args:
            rule_store: RuleStore instance to write to
        """
        self.store = rule_store

    # ── PRIVATE HELPERS ───────────────────────────────────────────────────────

    def _enrich_target(self, rule: dict) -> dict:
        """
        Auto-correct plain entity names to proper IFC class names.
        If the LLM returns "stair" instead of "IfcStairFlight", this fixes it.
        Works on the 'target' field (formerly 'entity_type').
        """
        target = rule.get("target", "")

        # Already a valid IFC class — leave it
        if str(target).startswith("Ifc"):
            return rule

        # Try to match against the OBC → IFC map
        target_lower = target.lower()
        for keyword, ifc_class in OBC_TO_IFC_MAP.items():
            if keyword in target_lower:
                rule["target"] = ifc_class
                return rule

        # Could not map — leave as-is, validation will catch it
        return rule

    def _enrich_property_set(self, rule: dict) -> dict:
        """
        Auto-fill property_set when the LLM omits it, using the IFC class
        as a lookup key into IFC_PROPERTY_SET_MAP.
        """
        if rule.get("property_set"):
            return rule  # already set

        target = rule.get("target", "")
        pset = IFC_PROPERTY_SET_MAP.get(target)
        if pset:
            rule["property_set"] = pset
        return rule

    def _apply_defaults(self, rule: dict) -> dict:
        """
        Ensure all standard fields exist with safe defaults so Module 4
        always gets a consistent shape regardless of how sparse the LLM output was.
        """
        defaults = {
            "ref": "",
            "desc": "",
            "source_text": "",
            "target": "Unspecified",
            "property_set": "",
            "property_name": "",
            "fallback_property": "",
            "rule_type": "numeric_comparison",
            "operator": ">=",
            "check_value": None,
            "value_min": None,
            "value_max": None,
            "unit": "",
            "applies_when": {},
            "severity": "mandatory",
            "keyword": "shall",
            "compliance_type": "prescriptive",
            "exceptions": [],
            "related_refs": [],
            "overridden_by": None,
            "confidence": 0.8,
            "extraction_method": "llm",
            "needs_review": False,
        }
        for key, val in defaults.items():
            if key not in rule:
                rule[key] = val
        return rule

    def _validate(self, rule: dict) -> tuple:
        """
        Validate that a rule has all required fields and valid values.
        Validation is rule-type-aware: each rule type has its own required fields
        as defined in RULE_TYPE_REQUIRED_FIELDS.

        Returns:
            tuple: (is_valid: bool, reason: str)
        """
        # Always-required fields (regardless of rule type)
        for field in _ALWAYS_REQUIRED:
            if not rule.get(field):
                return False, f"Missing required field: '{field}'"

        # Valid rule type
        rule_type = rule["rule_type"]
        if rule_type not in VALID_RULE_TYPES:
            return False, (f"Invalid rule_type: '{rule_type}' — must be one of {VALID_RULE_TYPES}")

        # Rule-type-aware required fields
        required_for_type = RULE_TYPE_REQUIRED_FIELDS.get(rule_type, [])
        for field in required_for_type:
            if field == "check_value":
                # check_value not required for existence operators
                operator = rule.get("operator", "")
                if operator in _VALUE_OPERATORS:
                    continue
                if rule.get("check_value") is None:
                    return False, (
                        f"Missing 'check_value' for rule_type '{rule_type}' "
                        f"with operator '{operator}'"
                    )
            elif field in ("value_min", "value_max"):
                if rule.get(field) is None:
                    return False, (
                        f"Missing '{field}' for rule_type '{rule_type}' "
                        "(required for numeric_range)"
                    )
            elif not rule.get(field):
                return False, (f"Missing required field '{field}' for rule_type '{rule_type}'")

        # Valid operator (only checked when an operator is present)
        operator = rule.get("operator", "")
        if operator and operator not in VALID_OPERATORS:
            return False, (f"Invalid operator: '{operator}' — must be one of {VALID_OPERATORS}")

        # between must have value_min and value_max (not a list in value)
        if operator == "between":
            if rule.get("value_min") is None or rule.get("value_max") is None:
                return False, (
                    "Operator 'between' requires 'value_min' and 'value_max' "
                    "(do not use a list in 'check_value')"
                )

        return True, "OK"

    # ── PUBLIC API ────────────────────────────────────────────────────────────

    def save_single(self, rule: dict, source_doc: str = SOURCE_DOC_PDF) -> str | None:
        """
        Validate, enrich, and save one rule to the database.

        Args:
            rule       (dict): raw rule dict from LLM or manual seed
            source_doc (str):  label for the source document

        Returns:
            str | None: rule_id if saved, None if invalid
        """
        rule["source_doc"] = source_doc
        rule = self._apply_defaults(rule)
        rule = self._enrich_target(rule)
        rule = self._enrich_property_set(rule)
        valid, reason = self._validate(rule)

        if valid:
            return self.store.save_rule(rule)
        else:
            ref = rule.get("ref", "?")
            desc = rule.get("desc", "")[:60]
            print(f"  [SKIPPED] [{ref}] {reason} | {desc}")
            return None

    def save_batch(self, rules: list, source_doc: str = SOURCE_DOC_PDF) -> list:
        """
        Validate and save a list of rules.
        Skips invalid rules and logs the reason.

        Args:
            rules      (list[dict]): list of raw rule dicts
            source_doc (str):        label for the source document

        Returns:
            list[str]: list of saved rule_ids
        """
        saved_ids = []

        for rule in rules:
            rule_id = self.save_single(rule, source_doc)
            if rule_id:
                saved_ids.append(rule_id)

        total = len(rules)
        saved = len(saved_ids)
        skipped = total - saved

        print(f"  [RuleGenerator] Saved {saved}/{total} rules ({skipped} skipped)")

        return saved_ids
