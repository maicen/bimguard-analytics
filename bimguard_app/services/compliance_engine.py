"""Rule-evaluation engine that runs typed compliance checks against IFC models."""

from datetime import datetime
from pathlib import Path
from typing import List

import ifcopenshell

from app.models.compliance_models import ComplianceCheck, ComplianceSummary
from app.models.rule_models import Rule, RuleType
from app.services.rule_evaluators.geometric import GeometricEvaluator
from app.services.rule_evaluators.metadata import MetadataEvaluator
from app.services.rule_evaluators.naming import NamingEvaluator


class ComplianceEngine:
    """Coordinate rule evaluators and aggregate their compliance results."""

    def __init__(self):
        """Initialize evaluator instances mapped by rule type."""
        self.evaluators = {
            RuleType.NOMENCLATURE: NamingEvaluator(),
            RuleType.METADATA: MetadataEvaluator(),
            RuleType.SPATIAL: GeometricEvaluator(),
        }

    def run_check(self, ifc_path: Path, rules: List[Rule]) -> ComplianceCheck:
        """Evaluate all provided rules against an IFC file and return a check summary."""
        ifc_file = ifcopenshell.open(str(ifc_path))
        all_issues = []

        for rule in rules:
            evaluator = self.evaluators.get(rule.type)
            if evaluator:
                issues = evaluator.evaluate(ifc_file, rule)
                all_issues.extend(issues)

        # Basic summary calculation
        summary = ComplianceSummary(
            critical=len([i for i in all_issues if "VIOLATION" in i.type]),
            warnings=len([i for i in all_issues if "MISSING" in i.type]),
            passed=0,  # Needs actual element count logic for accuracy
        )

        from uuid import uuid4

        return ComplianceCheck(
            id=uuid4(),  # generate a unique ID for each check rather than reusing rule document
            filename=ifc_path.name,
            status="completed",
            created_at=datetime.now(),
            completed_at=datetime.now(),
            summary=summary,
            issues=all_issues,
        )
