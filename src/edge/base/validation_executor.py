from __future__ import annotations
from edge.base.validation_result import EdgeValidationResult
from edge.base.validation_rule import EdgeValidationRule

class EdgeValidationExecutor:
    def execute(self, rule: EdgeValidationRule, edge_snapshot: dict) -> EdgeValidationResult:
        return rule.run(edge_snapshot)
