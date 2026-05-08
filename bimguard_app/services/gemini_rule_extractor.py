"""Gemini-based rule extraction provider used by the rule extraction pipeline."""

import json
import os
from typing import Protocol

from litellm import acompletion


class RuleExtractionProvider(Protocol):
    """Protocol for asynchronous rule extraction providers."""

    async def extract_rules_from_text(
        self, text: str, *, chunk_index: int, total_chunks: int
    ) -> list[dict]:
        """Extract structured rule dictionaries from a text chunk."""
        ...


_SYSTEM_PROMPT = """\
You are a BIM compliance rule extraction engine for building regulations (e.g. OBC Part 9).

Extract every discrete, checkable requirement from the text and return a JSON object with
a top-level "rules" array. Each rule MUST have ALL of the following fields:

{
  "ref":               "section reference e.g. 9.8.2.1.(1), or empty string",
  "desc":              "short plain-English rule description",
  "source_text":       "exact quote or close paraphrase from the regulation",

  "target":            "IFC class the rule applies to e.g. IfcStairFlight",
  "property_set":      "Pset name e.g. Pset_StairFlightCommon, or null",
  "property_name":     "IFC property to measure e.g. TreadLength, or null",
  "fallback_property": "alternative property name if primary missing, or null",

  "rule_type":         "numeric_range | exists_check | regex_match | classification",
  "operator":          ">= | <= | == | != | between | exists | matches",
  "value":             860,
  "value_min":         null,
  "value_max":         null,
  "unit":              "mm | m | m2 | deg | ratio | null",

  "applies_when": {
    "building_use":  "residential | commercial | any",
    "max_storeys":   null,
    "location":      "exit | interior | exterior | any"
  },

  "severity":          "mandatory | recommended | informational",
  "keyword":           "shall | must | should | may",
  "compliance_type":   "prescriptive | performance | descriptive",

  "exceptions":        ["list of exception strings, or empty array"],
  "related_refs":      ["related section numbers, or empty array"],
  "overridden_by":     null,

  "confidence":        0.9,
  "extraction_method": "llm",
  "needs_review":      false
}

RULES:
- Output ONLY valid JSON — no markdown, no prose, no code fences.
- Use "between" operator + value_min/value_max for min-and-max requirements; set "value" to null.
- Use "exists" operator + value null for presence-only checks.
- Set confidence < 0.7 and needs_review true when the text is ambiguous.
- Skip commentary, examples, definitions, and duplicate rules.
- Exclude requirements that cannot be expressed as a discrete checkable rule.\
"""


class LiteLLMGeminiRuleExtractor:
    """Extracts structured compliance rules from text chunks using Gemini."""

    def __init__(self, *, model: str | None = None, temperature: float = 0):
        """Create a Gemini extractor with optional model and temperature overrides."""
        self._model = model or os.getenv("BIM_GUARD_RULE_MODEL", "gemini/gemini-2.0-flash")
        self._temperature = temperature

    async def extract_rules_from_text(
        self, text: str, *, chunk_index: int, total_chunks: int
    ) -> list[dict]:
        """Call Gemini and normalize extracted rules for a single text chunk."""
        if not text.strip():
            return []

        self._ensure_api_key()

        user_prompt = (
            f"This is chunk {chunk_index} of {total_chunks}. "
            "Extract all BIM compliance rules from the text below. "
            "Return JSON only.\n\nTEXT:\n" + text
        )

        response = await acompletion(
            model=self._model,
            messages=[
                {"role": "system", "content": _SYSTEM_PROMPT},
                {"role": "user", "content": user_prompt},
            ],
            response_format={"type": "json_object"},
            temperature=self._temperature,
        )
        payload = self._parse(response.choices[0].message.content)
        return self._normalize(payload.get("rules", []))

    # ── Private ───────────────────────────────────────────────────────────────

    def _ensure_api_key(self):
        if os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY"):
            return
        raise RuntimeError(
            "Gemini API key is not configured. Set GEMINI_API_KEY or GOOGLE_API_KEY."
        )

    def _parse(self, content) -> dict:
        if isinstance(content, list):
            content = "".join(part.get("text", "") for part in content if isinstance(part, dict))
        if not isinstance(content, str) or not content.strip():
            return {"rules": []}

        cleaned = content.strip().lstrip("`")
        if cleaned.startswith("json"):
            cleaned = cleaned[4:].strip()

        try:
            parsed = json.loads(cleaned)
        except json.JSONDecodeError:
            return {"rules": []}

        if isinstance(parsed, list):
            return {"rules": parsed}
        if isinstance(parsed, dict):
            return parsed
        return {"rules": []}

    def _normalize(self, rules: list) -> list[dict]:
        normalized = []
        for idx, rule in enumerate(rules, start=1):
            if not isinstance(rule, dict):
                continue

            desc = str(rule.get("desc") or rule.get("description") or "").strip()
            if not desc:
                continue

            ref = str(rule.get("ref") or rule.get("reference") or "").strip()
            applies_when = rule.get("applies_when") or {}
            if not isinstance(applies_when, dict):
                applies_when = {}

            normalized.append(
                {
                    "ref": ref or f"REQ-AI-{idx:03d}",
                    "desc": desc,
                    "source_text": str(rule.get("source_text") or "").strip(),
                    "target": str(
                        rule.get("target") or rule.get("target_ifc_class") or "Unspecified"
                    ).strip(),
                    "property_set": str(rule.get("property_set") or "").strip(),
                    "property_name": str(rule.get("property_name") or "").strip(),
                    "fallback_property": str(rule.get("fallback_property") or "").strip(),
                    "rule_type": str(rule.get("rule_type") or "numeric_range").strip(),
                    "operator": str(rule.get("operator") or ">=").strip(),
                    "value": rule.get("value"),
                    "value_min": rule.get("value_min"),
                    "value_max": rule.get("value_max"),
                    "unit": str(rule.get("unit") or "").strip(),
                    "applies_when": applies_when,
                    "severity": str(rule.get("severity") or "mandatory").strip(),
                    "keyword": str(rule.get("keyword") or "shall").strip(),
                    "compliance_type": str(rule.get("compliance_type") or "prescriptive").strip(),
                    "exceptions": rule.get("exceptions") or [],
                    "related_refs": rule.get("related_refs") or [],
                    "overridden_by": rule.get("overridden_by"),
                    "confidence": float(rule.get("confidence") or 0.8),
                    "extraction_method": "llm",
                    "needs_review": bool(rule.get("needs_review", False)),
                }
            )

        return normalized
