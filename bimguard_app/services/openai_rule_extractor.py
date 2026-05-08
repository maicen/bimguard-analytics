import json
import os

from openai import AsyncOpenAI


class RuleExtractionProvider:
    async def extract_rules_from_text(
        self, text: str, *, chunk_index: int, total_chunks: int
    ) -> list[dict]: ...


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


class OpenAIRuleExtractor:
    """Extracts structured compliance rules from text chunks using OpenAI."""

    def __init__(self, *, model: str | None = None, temperature: float = 0):
        self._model = model or os.getenv("BIM_GUARD_RULE_MODEL", "gpt-4o-mini")
        self._temperature = temperature
        self._client: AsyncOpenAI | None = None

    def _get_client(self) -> AsyncOpenAI:
        """Lazy-initialize so the service can be imported without an API key."""
        if self._client is None:
            self._ensure_api_key()
            self._client = AsyncOpenAI()
        return self._client

    async def extract_rules_from_text(
        self, text: str, *, chunk_index: int, total_chunks: int
    ) -> list[dict]:
        if not text.strip():
            return []

        client = self._get_client()

        user_prompt = (
            f"This is chunk {chunk_index} of {total_chunks}. "
            "Extract all BIM compliance rules from the text below. "
            "Return JSON only.\n\nTEXT:\n" + text
        )

        response = await client.chat.completions.create(
            model=self._model,
            messages=[
                {"role": "system", "content": _SYSTEM_PROMPT},
                {"role": "user",   "content": user_prompt},
            ],
            response_format={"type": "json_object"},
            temperature=self._temperature,
        )
        if not response.choices:
            return []
        payload = self._parse(response.choices[0].message.content)
        return self._normalize(payload.get("rules", []))

    # ── Private ───────────────────────────────────────────────────────────────

    def _ensure_api_key(self):
        if os.getenv("OPENAI_API_KEY"):
            return
        raise RuntimeError(
            "OpenAI API key is not configured. "
            "Copy example.env to .env and set OPENAI_API_KEY, then restart."
        )

    def _parse(self, content) -> dict:
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

            # LLM may return "value" or "check_value" — normalise to both so
            # the web UI displays it and Module 3 / RuleGenerator can consume it.
            check_value = rule.get("value") if rule.get("value") is not None \
                          else rule.get("check_value")

            normalized.append({
                "ref":               ref or f"REQ-AI-{idx:03d}",
                "desc":              desc,
                "source_text":       str(rule.get("source_text") or "").strip(),

                "target":            str(rule.get("target") or rule.get("target_ifc_class") or "Unspecified").strip(),
                "property_set":      str(rule.get("property_set") or "").strip(),
                "property_name":     str(rule.get("property_name") or "").strip(),
                "fallback_property": str(rule.get("fallback_property") or "").strip(),

                "rule_type":         str(rule.get("rule_type") or "numeric_range").strip(),
                "operator":          str(rule.get("operator") or ">=").strip(),
                "value":             check_value,        # display / UI key
                "check_value":       check_value,        # Module 3 / RuleGenerator key
                "value_min":         rule.get("value_min"),
                "value_max":         rule.get("value_max"),
                "unit":              str(rule.get("unit") or "").strip(),

                "applies_when":      applies_when,
                "severity":          str(rule.get("severity") or "mandatory").strip(),
                "keyword":           str(rule.get("keyword") or "shall").strip(),
                "compliance_type":   str(rule.get("compliance_type") or "prescriptive").strip(),

                "exceptions":        rule.get("exceptions") or [],
                "related_refs":      rule.get("related_refs") or [],
                "overridden_by":     rule.get("overridden_by"),

                "confidence":        float(rule.get("confidence") or 0.8),
                "extraction_method": "llm",
                "needs_review":      bool(rule.get("needs_review", False)),
            })

        return normalized
