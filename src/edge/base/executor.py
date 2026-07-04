from __future__ import annotations

from edge.base.result import EdgeRuleResult
from edge.base.rule import EdgeRule


class EdgeRuleExecutor:
    def execute(self, rule: EdgeRule, signal_snapshot: dict) -> EdgeRuleResult:
        return rule.run(signal_snapshot)
