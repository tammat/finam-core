from __future__ import annotations

from risk.base.result import RiskRuleResult
from risk.base.rule import RiskRule


class RiskRuleExecutor:
    def execute(self, rule: RiskRule, edge_decision: dict) -> RiskRuleResult:
        return rule.run(edge_decision)
