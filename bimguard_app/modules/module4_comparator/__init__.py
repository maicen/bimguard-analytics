"""
module4_comparator.py
----------------------
Compares IFC property values extracted by Module 2 against the rule library.

For each rule:
  - Applies operator + threshold(s) to every matching element
  - Returns PASS / FAIL / MISSING_DATA / PARTIAL / NO_ELEMENTS per rule
  - Collects per-element failure details for Module 5 reporting

Operators: >= <= > < == != between exists not_exists matches
"""

import re


class Module4_Comparator:
    """Validates IFC model data against the BIMGuard rule library."""

    # ── Public API ────────────────────────────────────────────────────────────

    def validate_metadata(self, extraction_results: list[dict]) -> list[dict]:
        """
        Main entry point. Takes Module2_IFCRead.extract_for_compliance() output
        and returns one compliance record per rule.

        Args:
            extraction_results: list[dict] from Module 2

        Returns:
            list[dict] with status, counts, and per-element failures
        """
        return [self._evaluate_rule(item) for item in extraction_results]

    def check_naming_conventions(self, elements: list, patterns: list[str]) -> list[dict]:
        """Check element names against regex naming patterns."""
        issues = []
        for el in elements:
            name = el.get("name", "")
            for pattern in patterns:
                try:
                    if not re.fullmatch(pattern, name):
                        issues.append({"guid": el.get("guid"), "name": name,
                                       "pattern": pattern, "status": "FAIL"})
                except re.error:
                    pass
        return issues

    def check_spatial_clearances(self, extraction_results: list[dict]) -> list[dict]:
        """Evaluate spatial clearance rules — delegates to validate_metadata."""
        clearance = [r for r in extraction_results if r.get("operator") == "between"]
        return self.validate_metadata(clearance)

    # ── Private ───────────────────────────────────────────────────────────────

    def _evaluate_rule(self, item: dict) -> dict:
        operator  = item.get("operator", "")
        check_val = item.get("check_value")
        val_min   = item.get("value_min")
        val_max   = item.get("value_max")
        unit      = item.get("unit", "")
        elements  = item.get("elements", [])

        if not elements:
            return self._result(item, "NO_ELEMENTS", 0, 0, 0, 0, [])

        pass_count = fail_count = missing_count = 0
        failures: list[dict] = []

        for el in elements:
            actual = el.get("actual_value")

            if operator in ("exists", "not_exists"):
                present = actual is not None
                wanted  = operator == "exists"
                if present == wanted:
                    pass_count += 1
                else:
                    fail_count += 1
                    failures.append(self._failure(
                        el, actual,
                        "property missing" if wanted else "property should not exist"))
                continue

            if actual is None:
                missing_count += 1
                continue

            passed, reason = self._compare(operator, actual, check_val, val_min, val_max, unit)
            if passed:
                pass_count += 1
            else:
                fail_count += 1
                failures.append(self._failure(el, actual, reason))

        if fail_count > 0:
            status = "FAIL"
        elif missing_count > 0 and pass_count == 0:
            status = "MISSING_DATA"
        elif missing_count > 0:
            status = "PARTIAL"
        else:
            status = "PASS"

        return self._result(item, status, pass_count, fail_count,
                            missing_count, len(elements), failures)

    def _compare(self, operator, actual, check_val, val_min, val_max, unit):
        try:
            a = float(str(actual).replace(",", "").strip())
        except (ValueError, TypeError):
            if operator == "==":
                ok = str(actual) == str(check_val)
            elif operator == "!=":
                ok = str(actual) != str(check_val)
            elif operator == "matches" and check_val:
                try:
                    ok = bool(re.search(str(check_val), str(actual)))
                except re.error:
                    ok = False
            else:
                ok = False
            return ok, ("" if ok else f'"{actual}" fails {operator} "{check_val}"')

        u = f" {unit}" if unit else ""
        if operator == ">=":
            ok, reason = check_val is not None and a >= check_val, \
                         f"{a}{u} < required {check_val}{u}"
        elif operator == "<=":
            ok, reason = check_val is not None and a <= check_val, \
                         f"{a}{u} > maximum {check_val}{u}"
        elif operator == ">":
            ok, reason = check_val is not None and a > check_val, \
                         f"{a}{u} ≤ required {check_val}{u}"
        elif operator == "<":
            ok, reason = check_val is not None and a < check_val, \
                         f"{a}{u} ≥ maximum {check_val}{u}"
        elif operator == "==":
            ok, reason = check_val is not None and a == check_val, \
                         f"{a}{u} ≠ {check_val}{u}"
        elif operator == "!=":
            ok, reason = check_val is not None and a != check_val, \
                         f"{a}{u} equals excluded value {check_val}{u}"
        elif operator == "between":
            ok = val_min is not None and val_max is not None and val_min <= a <= val_max
            reason = f"{a}{u} outside [{val_min}{u}–{val_max}{u}]"
        else:
            ok, reason = True, ""

        return ok, ("" if ok else reason)

    @staticmethod
    def _failure(el, actual, reason) -> dict:
        return {"element_name": el.get("name"), "guid": el.get("guid"),
                "actual": actual, "reason": reason}

    @staticmethod
    def _result(item, status, pass_count, fail_count, missing_count, total, failures) -> dict:
        return {
            "rule_ref":      item.get("rule_ref", ""),
            "rule_desc":     item.get("rule_desc", ""),
            "target":        item.get("target_ifc_class", ""),
            "property_name": item.get("property_name", ""),
            "property_set":  item.get("property_set", ""),
            "operator":      item.get("operator", ""),
            "check_value":   item.get("check_value"),
            "value_min":     item.get("value_min"),
            "value_max":     item.get("value_max"),
            "unit":          item.get("unit", ""),
            "severity":      item.get("severity", "mandatory"),
            "status":        status,
            "pass_count":    pass_count,
            "fail_count":    fail_count,
            "missing_count": missing_count,
            "total_count":   total,
            "failures":      failures,
        }
