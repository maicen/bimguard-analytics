"""
module1_doc_parser/table_rule_builder.py
------------------------------------------
Step 2 — Converts Docling table DataFrames directly into rules.db entries.
No LLM required for tables — Min/Max columns map directly to numeric_range rules.

Usage:
    from module1_doc_parser.table_rule_builder import TableRuleBuilder
    builder = TableRuleBuilder(store)
    builder.process_all_tables(tables, generator)
"""

TABLE_ENTITY_MAP = {
    "stair": "IfcStairFlight",
    "riser": "IfcStairFlight",
    "tread": "IfcStairFlight",
    "rise": "IfcStairFlight",
    "run": "IfcStairFlight",
    "nosing": "IfcStairFlight",
    "door": "IfcDoor",
    "doorway": "IfcDoor",
    "window": "IfcWindow",
    "glazing": "IfcWindow",
    "ramp": "IfcRamp",
    "slope": "IfcRamp",
    "guard": "IfcRailing",
    "handrail": "IfcRailing",
    "landing": "IfcSlab",
    "floor": "IfcSlab",
    "wall": "IfcWall",
}

MIN_VARIANTS = {"min", "minimum", "min (mm)", "min. (mm)", "min.", "minimum (mm)"}
MAX_VARIANTS = {"max", "maximum", "max (mm)", "max. (mm)", "max.", "maximum (mm)"}


class TableRuleBuilder:
    def __init__(self, rule_store=None):
        self.store = rule_store

    def _detect_target(self, text: str) -> str:
        text_lower = str(text).lower()
        for kw, ifc in TABLE_ENTITY_MAP.items():
            if kw in text_lower:
                return ifc
        return "IfcBuildingElement"

    def _detect_unit(self, text: str) -> str:
        t = str(text).lower()
        if "m2" in t or "area" in t:
            return "m2"
        if "deg" in t or "angle" in t:
            return "deg"
        return "mm"

    def _build_rule_dicts(self, table_dict: dict) -> list[dict]:
        """Build rule dicts from a table DataFrame without saving to any store."""
        df = table_dict["dataframe"].copy()
        idx = table_dict["table_index"]
        df.columns = [str(c).strip().lower() for c in df.columns]

        min_col = next((c for c in df.columns if c in MIN_VARIANTS), None)
        max_col = next((c for c in df.columns if c in MAX_VARIANTS), None)
        if not min_col or not max_col:
            return []

        prop_col = df.columns[0]
        rules = []

        for _, row in df.iterrows():
            name = str(row.get(prop_col, "")).strip()
            if not name or name.lower() == "nan":
                continue
            try:
                min_val = float(str(row[min_col]).replace(",", "").strip())
                max_val = float(str(row[max_col]).replace(",", "").strip())
            except (ValueError, TypeError):
                continue

            rules.append(
                {
                    "ref": f"OBC_Table_{idx + 1}",
                    "desc": f"{name} must be between {min_val} and {max_val}",
                    "source_text": "",
                    "target": self._detect_target(name),
                    "property_set": "",
                    "property_name": name.replace(" ", "_").title(),
                    "fallback_property": "",
                    "rule_type": "numeric_range",
                    "operator": "between",
                    "value": None,  # table rules use value_min/value_max
                    "check_value": None,  # Module 3 compatibility
                    "value_min": min_val,
                    "value_max": max_val,
                    "unit": self._detect_unit(name),
                    "applies_when": {},
                    "severity": "mandatory",
                    "keyword": "shall",
                    "compliance_type": "prescriptive",
                    "exceptions": [],
                    "related_refs": [],
                    "overridden_by": None,
                    "confidence": 1.0,
                    "extraction_method": "table",
                    "needs_review": False,
                }
            )

        return rules

    def extract_all_as_dicts(self, tables: list) -> list[dict]:
        """Return all table rules as dicts without saving to any store."""
        all_rules: list[dict] = []
        for t in tables:
            all_rules.extend(self._build_rule_dicts(t))
        if all_rules:
            print(
                f"[TableRuleBuilder] {len(all_rules)} table rules built from {len(tables)} tables"
            )
        return all_rules

    def _extract_from_table(self, table_dict: dict, generator) -> int:
        rules = self._build_rule_dicts(table_dict)
        if rules:
            saved = generator.save_batch(rules, source_doc="OBC_Table_Direct")
            return len(saved)
        return 0

    def process_all_tables(self, tables: list, generator) -> int:
        if not tables:
            print("[TableRuleBuilder] No tables found")
            return 0

        print(f"[TableRuleBuilder] Processing {len(tables)} tables...")
        total = 0
        for t in tables:
            saved = self._extract_from_table(t, generator)
            idx = t["table_index"]
            if saved:
                print(f"  Table {idx + 1}: {saved} rules saved (no LLM)")
            else:
                print(f"  Table {idx + 1}: no Min/Max columns — skipped")
            total += saved

        print(f"[TableRuleBuilder] Done — {total} rules saved")
        return total
