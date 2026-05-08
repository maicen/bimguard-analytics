"""
tests/test_module3.py
----------------------
Unit tests for Module 3 — RuleGenerator (validation/enrichment path), RuleStore,
rule schema validation, and edge cases.

Run with: pytest tests/test_module3.py -v

Test groups:
  - RuleStore:           basic CRUD, get_all_rules, clear
  - RuleGenerator:       enrichment, validation, save_batch
  - Schema validation:   field checks against the rich schema
  - LLM (RuleConverter): calls the real LLM — skip if no API key
    Run:  pytest tests/test_module3.py -m llm -v
    Skip: pytest tests/test_module3.py -m "not llm" -v
"""

import json
import os

import pytest
from module3_rule_builder.rule_generator import RuleGenerator
from module3_rule_builder.rule_store import RuleStore

TEST_DB = "tests/test_rules_m3.db"


# ═══════════════════════════════════════════════════════════════════════════════
# Fixtures
# ═══════════════════════════════════════════════════════════════════════════════


@pytest.fixture
def store():
    s = RuleStore(TEST_DB)
    s.clear_all_rules()
    yield s
    s.close()
    if os.path.exists(TEST_DB):
        os.remove(TEST_DB)


@pytest.fixture
def gen(store):
    return RuleGenerator(store)


# ═══════════════════════════════════════════════════════════════════════════════
# RuleStore — basic operations
# ═══════════════════════════════════════════════════════════════════════════════


def test_store_starts_empty(store):
    assert store.count() == 0


def test_store_save_and_retrieve(store):
    rule = {
        "ref": "9.8.2.1.(2)",
        "rule_type": "numeric_comparison",
        "target": "IfcStairFlight",
        "property_name": "Width",
        "operator": ">=",
        "check_value": 860,
        "unit": "mm",
        "severity": "mandatory",
        "desc": "Exit stair minimum width 860 mm",
    }
    store.save_rule(rule)
    assert store.count() == 1

    rules = store.get_all_rules()
    assert len(rules) == 1
    assert rules[0]["target"] == "IfcStairFlight"
    assert rules[0]["check_value"] == 860


def test_store_clear(store):
    store.save_rule(
        {
            "ref": "A",
            "rule_type": "numeric_comparison",
            "target": "IfcStairFlight",
            "property_name": "Width",
            "operator": ">=",
            "check_value": 860,
            "desc": "stair width",
            "severity": "mandatory",
        }
    )
    store.save_rule(
        {
            "ref": "B",
            "rule_type": "numeric_comparison",
            "target": "IfcDoor",
            "property_name": "ClearWidth",
            "operator": ">=",
            "check_value": 800,
            "desc": "door width",
            "severity": "mandatory",
        }
    )
    assert store.count() == 2
    store.clear_all_rules()
    assert store.count() == 0


def test_store_get_all_rules_returns_dicts(store):
    store.save_rule(
        {
            "ref": "9.8.2",
            "rule_type": "numeric_comparison",
            "target": "IfcStairFlight",
            "property_name": "Width",
            "operator": ">=",
            "check_value": 860,
            "desc": "stair",
            "severity": "mandatory",
        }
    )
    rules = store.get_all_rules()
    assert isinstance(rules, list)
    assert isinstance(rules[0], dict)


def test_store_fetch_rules_for_target(store):
    store.save_rule(
        {
            "ref": "R1",
            "rule_type": "numeric_comparison",
            "target": "IfcStairFlight",
            "property_name": "Width",
            "operator": ">=",
            "check_value": 860,
            "desc": "stair width",
            "severity": "mandatory",
        }
    )
    store.save_rule(
        {
            "ref": "R2",
            "rule_type": "numeric_comparison",
            "target": "IfcDoor",
            "property_name": "Height",
            "operator": ">=",
            "check_value": 1980,
            "desc": "door height",
            "severity": "mandatory",
        }
    )
    stair_rules = store.fetch_rules_for_target("IfcStairFlight")
    assert len(stair_rules) == 1
    assert stair_rules[0]["target"] == "IfcStairFlight"


def test_store_handles_duplicate_rules(store):
    """Saving the same rule twice should not crash."""
    rule = {
        "ref": "X",
        "rule_type": "numeric_comparison",
        "target": "IfcStairFlight",
        "property_name": "Width",
        "operator": ">=",
        "check_value": 860,
        "desc": "dup",
        "severity": "mandatory",
    }
    store.save_rule(rule)
    store.save_rule(rule)
    assert store.count() >= 1


# ═══════════════════════════════════════════════════════════════════════════════
# Schema validation helper
# ═══════════════════════════════════════════════════════════════════════════════

REQUIRED_RULE_FIELDS = {"target", "property_name", "operator", "rule_type", "desc"}

VALID_OPERATORS = {
    ">=",
    "<=",
    "==",
    "!=",
    "between",
    "exists",
    "not_exists",
    "matches",
    "conforms_to",
}


def validate_rule_schema(rule_data: dict) -> list:
    """Returns list of issues. Empty list = valid."""
    issues = []

    missing = REQUIRED_RULE_FIELDS - set(rule_data.keys())
    if missing:
        issues.append(f"Missing fields: {missing}")

    if "operator" in rule_data:
        op = rule_data["operator"]
        if op not in VALID_OPERATORS:
            issues.append(f"Unknown operator: '{op}'")

    if "rule_type" in rule_data:
        from config import VALID_RULE_TYPES

        if rule_data["rule_type"] not in VALID_RULE_TYPES:
            issues.append(f"Unknown rule_type: '{rule_data['rule_type']}'")

    return issues


# ═══════════════════════════════════════════════════════════════════════════════
# RuleGenerator — enrichment and validation
# ═══════════════════════════════════════════════════════════════════════════════


def test_generator_enriches_plain_target(gen, store):
    """Plain word like 'stair' should be mapped to 'IfcStairFlight'."""
    rule = {
        "ref": "9.8",
        "rule_type": "numeric_comparison",
        "target": "stair",
        "property_name": "Width",
        "operator": ">=",
        "check_value": 860,
        "desc": "stair width",
        "severity": "mandatory",
    }
    gen.save_single(rule)
    rules = store.get_all_rules()
    assert rules[0]["target"] == "IfcStairFlight"


def test_generator_auto_fills_property_set(gen, store):
    """property_set should be auto-filled from IFC_PROPERTY_SET_MAP when omitted."""
    rule = {
        "ref": "9.8",
        "rule_type": "numeric_comparison",
        "target": "IfcStairFlight",
        "property_name": "Width",
        "operator": ">=",
        "check_value": 860,
        "desc": "stair width",
        "severity": "mandatory",
    }
    gen.save_single(rule)
    rules = store.get_all_rules()
    assert rules[0].get("property_set") == "Pset_StairFlightCommon"


def test_generator_skips_invalid_operator(gen, store):
    """A rule with an unrecognised operator should be rejected."""
    rule = {
        "ref": "9.8",
        "rule_type": "numeric_comparison",
        "target": "IfcStairFlight",
        "property_name": "Width",
        "operator": "GREATER_THAN",  # invalid
        "check_value": 860,
        "desc": "stair width",
        "severity": "mandatory",
    }
    result = gen.save_single(rule)
    assert result is None
    assert store.count() == 0


def test_generator_skips_invalid_rule_type(gen, store):
    """A rule with an old/unknown rule_type should be rejected."""
    rule = {
        "ref": "9.8",
        "rule_type": "json_check",  # old name
        "target": "IfcStairFlight",
        "property_name": "Width",
        "operator": ">=",
        "check_value": 860,
        "desc": "stair width",
        "severity": "mandatory",
    }
    result = gen.save_single(rule)
    assert result is None
    assert store.count() == 0


def test_generator_numeric_range_requires_min_max(gen, store):
    """numeric_range without value_min/value_max should be rejected."""
    rule = {
        "ref": "T9.8.4.1",
        "rule_type": "numeric_range",
        "target": "IfcStairFlight",
        "property_name": "RiserHeight",
        "operator": "between",
        "check_value": None,
        # value_min and value_max intentionally omitted
        "desc": "riser height range",
        "severity": "mandatory",
    }
    result = gen.save_single(rule)
    assert result is None


def test_generator_numeric_range_saves_with_min_max(gen, store):
    """numeric_range with value_min/value_max should save successfully."""
    rule = {
        "ref": "T9.8.4.1",
        "rule_type": "numeric_range",
        "target": "IfcStairFlight",
        "property_name": "RiserHeight",
        "operator": "between",
        "check_value": None,
        "value_min": 125,
        "value_max": 200,
        "unit": "mm",
        "desc": "riser height range",
        "severity": "mandatory",
    }
    result = gen.save_single(rule)
    assert result is not None
    assert store.count() == 1


def test_generator_exists_operator_skips_check_value(gen, store):
    """Exists operator should not require check_value."""
    rule = {
        "ref": "QA",
        "rule_type": "prohibition",
        "target": "IfcDoor",
        "property_name": "Width",
        "operator": "exists",
        "check_value": None,
        "desc": "door must have Width property",
        "severity": "informational",
    }
    result = gen.save_single(rule)
    assert result is not None


def test_generator_save_batch_counts_saved(gen, store):
    """save_batch should save valid rules and skip invalid ones."""
    rules = [
        {
            "ref": "A",
            "rule_type": "numeric_comparison",
            "target": "IfcStairFlight",
            "property_name": "Width",
            "operator": ">=",
            "check_value": 860,
            "desc": "stair width",
            "severity": "mandatory",
        },
        {
            "ref": "B",
            "rule_type": "json_check",  # invalid — should be skipped
            "target": "IfcDoor",
            "property_name": "Height",
            "operator": ">=",
            "check_value": 1980,
            "desc": "door height",
            "severity": "mandatory",
        },
        {
            "ref": "C",
            "rule_type": "numeric_range",
            "target": "IfcStairFlight",
            "property_name": "TreadDepth",
            "operator": "between",
            "check_value": None,
            "value_min": 255,
            "value_max": 355,
            "desc": "tread depth",
            "severity": "mandatory",
        },
    ]
    saved = gen.save_batch(rules)
    assert len(saved) == 2  # A and C pass; B fails
    assert store.count() == 2


# ═══════════════════════════════════════════════════════════════════════════════
# Seed rules smoke test (no LLM, no I/O)
# ═══════════════════════════════════════════════════════════════════════════════


def test_seed_rules_schema(gen, store):
    """All seed rules should pass schema validation."""
    from module3_rule_builder.obc_seed_rules import OBC_SEED_RULES

    saved = gen.save_batch(OBC_SEED_RULES, source_doc="OBC_Part9_Seed")
    assert len(saved) > 0, "At least some seed rules should save successfully"

    for rule in store.get_all_rules():
        issues = validate_rule_schema(rule)
        assert not issues, f"Seed rule failed schema check: {issues} — {rule.get('ref')}"


# ═══════════════════════════════════════════════════════════════════════════════
# LLM tests — RuleConverter (require GEMINI_API_KEY or GEMINI_API_KEY)
# ═══════════════════════════════════════════════════════════════════════════════

GOLDEN_CASES = [
    {
        "id": "stair_width",
        "text": "Every exit stair shall have a clear width of not less than 860 mm.",
        "expect": {"target_contains": "stair", "value": 860, "unit": "mm"},
    },
    {
        "id": "riser_height_range",
        "text": "The riser height shall be not less than 125 mm and not more than 200 mm.",
        "expect": {"target_contains": "stair", "value_min": 125, "value_max": 200},
    },
    {
        "id": "guard_height",
        "text": "Guards shall be not less than 900 mm in height measured vertically.",
        "expect": {"target_contains": "railing", "value": 900, "unit": "mm"},
    },
    {
        "id": "door_width",
        "text": "Every doorway in a means of egress shall have a clear width of not less than 810 mm.",
        "expect": {"target_contains": "door", "value": 810, "unit": "mm"},
    },
    {
        "id": "window_egress",
        "text": "Each window providing emergency egress shall have an unobstructed opening of not less than 0.35 m2.",
        "expect": {"target_contains": "window", "value": 0.35, "unit": "m2"},
    },
]


@pytest.mark.llm
class TestRuleConverterLLM:
    """
    Tests that call the real LLM (RuleConverter → GPT-4o).
    Requires GEMINI_API_KEY environment variable.
    Run with:  pytest tests/test_module3.py -m llm -v
    """

    @pytest.fixture
    def converter(self, store):
        from module3_rule_builder.rule_converter import RuleConverter

        api_key = os.getenv("GEMINI_API_KEY")
        if not api_key:
            pytest.skip("GEMINI_API_KEY not set")
        return RuleConverter(api_key=api_key, rule_store=store)

    @pytest.mark.parametrize("case", GOLDEN_CASES, ids=[c["id"] for c in GOLDEN_CASES])
    def test_golden_case_produces_valid_rule(self, converter, gen, store, case):
        """LLM should produce at least one structurally valid rule."""
        chunk = {
            "filtered_text": case["text"],
            "section_name": "Test",
            "section_number": "TEST",
            "count_high": 1,
            "count_medium": 0,
            "count_low": 0,
        }
        raw_rules = converter.extract_rules(chunk)
        assert len(raw_rules) >= 1, (
            f"[{case['id']}] No rules extracted from: {case['text'][:60]}..."
        )

        for rule in raw_rules:
            issues = validate_rule_schema(rule)
            assert not issues, f"[{case['id']}] Schema issues: {issues} — rule: {rule}"

    @pytest.mark.parametrize("case", GOLDEN_CASES, ids=[c["id"] for c in GOLDEN_CASES])
    def test_golden_case_correct_target(self, converter, gen, store, case):
        """Extracted rule should reference the correct IFC target class."""
        chunk = {
            "filtered_text": case["text"],
            "section_name": "Test",
            "section_number": "TEST",
            "count_high": 1,
            "count_medium": 0,
            "count_low": 0,
        }
        raw_rules = converter.extract_rules(chunk)
        assert raw_rules, f"[{case['id']}] No rules returned"

        rule = raw_rules[0]
        target_lower = rule.get("target", "").lower()
        expected = case["expect"]["target_contains"].lower()
        assert expected in target_lower, (
            f"[{case['id']}] Expected target containing '{expected}', got '{rule.get('target')}'"
        )

    def test_llm_handles_ambiguous_text(self, converter, gen, store):
        """Vague requirements should produce no rule or a needs_review rule."""
        chunk = {
            "filtered_text": "Adequate ventilation shall be provided in all occupied spaces.",
            "section_name": "Ventilation",
            "section_number": "V1",
            "count_high": 0,
            "count_medium": 1,
            "count_low": 0,
        }
        rules = converter.extract_rules(chunk)
        for rule in rules:
            if rule.get("check_value") is not None:
                assert rule.get("needs_review") or float(rule.get("confidence", 1)) < 0.7, (
                    f"LLM invented threshold without flagging: {rule}"
                )

    def test_llm_handles_multiple_requirements(self, converter, gen, store):
        """A chunk with 2 requirements should yield ~2 rules."""
        chunk = {
            "filtered_text": (
                "The riser height shall not be more than 200 mm. "
                "The tread run shall not be less than 255 mm."
            ),
            "section_name": "Stairs",
            "section_number": "9.8.4",
            "count_high": 2,
            "count_medium": 0,
            "count_low": 0,
        }
        rules = converter.extract_rules(chunk)
        assert len(rules) >= 2, f"Expected ≥2 rules from 2 requirements, got {len(rules)}"

    def test_llm_empty_input(self, converter, gen, store):
        """Empty string should return no rules, not crash."""
        chunk = {
            "filtered_text": "",
            "section_name": "Empty",
            "section_number": "0",
            "count_high": 0,
            "count_medium": 0,
            "count_low": 0,
        }
        rules = converter.extract_rules(chunk)
        assert rules == []


# ═══════════════════════════════════════════════════════════════════════════════
# Snapshot regression for Module 3 (non-LLM)
# ═══════════════════════════════════════════════════════════════════════════════

SNAPSHOTS_DIR = os.path.join(os.path.dirname(__file__), "snapshots")


class TestModule3Snapshots:
    def _snapshot_path(self, name):
        os.makedirs(SNAPSHOTS_DIR, exist_ok=True)
        return os.path.join(SNAPSHOTS_DIR, f"m3_{name}.json")

    def test_seed_rules_snapshot(self, gen, store):
        """Seed rules count and targets should not change unexpectedly."""
        from module3_rule_builder.obc_seed_rules import OBC_SEED_RULES

        gen.save_batch(OBC_SEED_RULES, source_doc="OBC_Part9_Seed")

        snap_file = self._snapshot_path("seed_rules_summary")
        current = store.summary()

        if not os.path.exists(snap_file):
            with open(snap_file, "w") as f:
                json.dump(current, f, indent=2)
            pytest.skip("Snapshot created — re-run to verify")

        with open(snap_file) as f:
            expected = json.load(f)

        assert current["total"] == expected["total"], (
            f"Seed rule count changed: {expected['total']} → {current['total']}"
        )
        assert set(current["by_entity"].keys()) == set(expected["by_entity"].keys()), (
            "Seed rule IFC targets changed"
        )
