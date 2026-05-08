"""
module3_rule_builder/rule_converter.py
----------------------------------------
NLP Engine — sends scored text chunks to GPT-4o and returns structured rules.
Uses RAG (Retrieval Augmented Generation) to ground the LLM output
in your existing rules.db schema — reducing hallucinations.

Responsibilities:
    - Build a guided system prompt using existing DB rules as examples
    - Send filtered section text to GPT-4o
    - Parse and return structured rule dicts
    - Handle JSON parse errors gracefully

Usage:
    from module3_rule_builder.rule_converter import RuleConverter
    from module3_rule_builder.rule_store import RuleStore
    from config import DB_PATH, GEMINI_API_KEY

    store     = RuleStore(DB_PATH)
    converter = RuleConverter(api_key=GEMINI_API_KEY, rule_store=store)
    rules     = converter.extract_rules(chunk)
"""

import json

import openai

try:
    from config import OPENAI_API_KEY, OPENAI_MODEL
except ImportError:
    from app.modules.config import OPENAI_API_KEY, OPENAI_MODEL


# ── SYSTEM PROMPT ─────────────────────────────────────────────────────────────
# RAG-guided: includes existing IFC targets and real example rules
# so the LLM always outputs the exact schema — not a guessed version.

RAG_SYSTEM_PROMPT = """\
You are a BIM compliance rule extraction engine for the Ontario Building Code (OBC) Part 9.

Extract every discrete checkable requirement as a JSON rule object.

SCHEMA — every rule must have ALL these fields:
{{
  "ref":               "OBC section number e.g. 9.8.2.1.(2), or empty string",
  "desc":              "short plain-English rule description",
  "source_text":       "exact quote or close paraphrase from the regulation",

  "target":            "IFC class e.g. IfcStairFlight | IfcDoor | IfcWindow | IfcRailing | IfcSlab | IfcWall | IfcRamp | IfcSpace | IfcZone | IfcColumn | IfcFooting | IfcBeam",
  "property_set":      "Pset name e.g. Pset_StairFlightCommon, or null",
  "property_name":     "exact IFC property name e.g. TreadLength, or null",
  "fallback_property": "alternative property name if primary missing, or null",

  "rule_type":         "numeric_comparison | numeric_range | prohibition | standard_conformance | deemed_to_comply | table_lookup | spatial_clearance | tiered",
  "operator":          ">= | <= | == | != | between | exists | not_exists | matches | conforms_to",
  "check_value":       860,
  "value_min":         null,
  "value_max":         null,
  "unit":              "mm | m | m2 | deg | ratio | null",

  "applies_when": {{
    "building_use":  "residential | commercial | any",
    "max_storeys":   null,
    "location":      "exit | interior | exterior | any"
  }},

  "severity":          "mandatory | recommended | informational",
  "keyword":           "shall | must | should | may",
  "compliance_type":   "prescriptive | performance | descriptive",

  "exceptions":        ["list of exception strings, or empty array"],
  "related_refs":      ["related section numbers, or empty array"],
  "overridden_by":     null,

  "confidence":        0.9,
  "extraction_method": "llm",
  "needs_review":      false
}}

RULE TYPE GUIDANCE:
- numeric_comparison  — single threshold check  e.g. Width >= 860 mm
- numeric_range       — band check using value_min/value_max  e.g. RiserHeight between 125–200 mm
- prohibition         — element or material must NOT be used  e.g. glass blocks as load-bearing
- standard_conformance— must conform to a referenced standard  e.g. ASTM C62 for masonry
- deemed_to_comply    — alternative compliance path  e.g. sprinklers in lieu of fire separation
- table_lookup        — value determined by a referenced table
- spatial_clearance   — clearance or headroom check  e.g. headroom >= 1950 mm
- tiered              — context-dependent thresholds  e.g. different widths per occupancy

OPERATOR GUIDANCE:
- Use "between" + value_min + value_max for min-and-max requirements; set check_value to null.
- Use "exists" + check_value null for property presence checks.
- Use "not_exists" for prohibitions where an element type must be absent.
- Use "conforms_to" for standard_conformance rules.

OUTPUT RULES:
- Output ONLY a valid JSON array. No markdown. No prose. No code fences.
- Skip commentary, examples, definitions, and duplicate rules.
- Do NOT duplicate rules for these already-known targets: {existing_targets}
- Set confidence < 0.7 and needs_review true when text is ambiguous.

EXAMPLE RULES FROM DATABASE (match this format exactly):
{rag_examples}

CURRENT SECTION BEING PROCESSED: {section_name}
PARAGRAPH CONFIDENCE BREAKDOWN: {high} HIGH | {medium} MEDIUM | {low} LOW_CONFIDENCE\
"""


class RuleConverter:
    """
    Sends filtered section chunks to GPT-4o and returns structured rule dicts.
    RAG-guided: pulls existing rules from DB as few-shot examples per call.
    """

    def __init__(self, api_key: str = None, rule_store=None, model: str = None):
        """
        Args:
            api_key    (str):       OpenAI API key (defaults to config.OPENAI_API_KEY)
            rule_store (RuleStore): RuleStore instance for RAG examples
            model      (str):       OpenAI model name (defaults to config.OPENAI_MODEL)
        """
        self.client = openai.OpenAI(api_key=api_key or OPENAI_API_KEY)
        self.store = rule_store
        self.model = model or OPENAI_MODEL

    # ── PRIVATE ───────────────────────────────────────────────────────────────

    def _build_system_prompt(self, chunk: dict) -> str:
        """
        Build a RAG-guided system prompt for this specific section chunk.
        Retrieves existing IFC targets and example rules from the DB
        so the LLM never guesses the schema.
        """
        existing_targets = []
        rag_examples = []

        if self.store:
            existing_targets = self.store.get_existing_entity_types()
            rag_examples = self.store.get_rules_sample(limit=3)

        return RAG_SYSTEM_PROMPT.format(
            existing_targets=", ".join(existing_targets) if existing_targets else "None yet",
            rag_examples=json.dumps(rag_examples, indent=2) if rag_examples else "None yet",
            section_name=chunk.get("section_name", "Unknown"),
            high=chunk.get("count_high", 0),
            medium=chunk.get("count_medium", 0),
            low=chunk.get("count_low", 0),
        )

    def _parse_response(self, raw: str, section_number: str) -> list:
        """
        Parse the LLM response string into a list of rule dicts.
        Strips markdown code fences if the LLM added them.
        """
        if raw.startswith("```"):
            raw = raw.split("```")[1]
            if raw.startswith("json"):
                raw = raw[4:]
        raw = raw.strip()

        try:
            parsed = json.loads(raw)
            if isinstance(parsed, list):
                return parsed
            if isinstance(parsed, dict):
                return parsed.get("rules", [parsed])
            return []
        except json.JSONDecodeError as e:
            print(f"  [RuleConverter] JSON parse error for section {section_number}: {e}")
            print(f"  Raw response preview: {raw[:300]}")
            return []

    # ── PUBLIC API ────────────────────────────────────────────────────────────

    def extract_rules(self, chunk: dict) -> list:
        """
        Send one scored section chunk to GPT-4o and return rule dicts.

        Args:
            chunk (dict): scored section chunk from keyword_filter.py
                          Must have keys: filtered_text, section_name,
                          section_number, count_high, count_medium, count_low

        Returns:
            list[dict]: raw rule dicts ready for RuleGenerator.save_batch()
        """
        text = chunk.get("filtered_text", "")

        # Skip sections with too little content after filtering
        if not text or len(text.strip()) < 50:
            section = chunk.get("section_number", "?")
            print(f"  [RuleConverter] Skipping Section {section} — too little text after filtering")
            return []

        system_prompt = self._build_system_prompt(chunk)

        response = self.client.chat.completions.create(
            model=self.model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": f"Extract all rules from this OBC section:\n\n{text}"},
            ],
            temperature=0.1,
        )

        raw = response.choices[0].message.content.strip()
        rules = self._parse_response(raw, chunk.get("section_number", "?"))

        # Tag each rule with its source section
        for rule in rules:
            rule["obc_section_number"] = chunk.get("section_number")
            rule["obc_section_name"] = chunk.get("section_name")

        return rules
