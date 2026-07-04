from __future__ import annotations

import time
from typing import Any

from risk.base.registry import RiskRuleRegistry
from risk.base.result import RiskRuleDiagnostics, RiskRuleResult
from risk.base.rule import RiskRule
from risk.default_rule.config import DefaultRiskRuleConfig


def _num(value: object, default: float = 0.0) -> float:
    try:
        return default if value is None else float(value)
    except (TypeError, ValueError):
        return default


def _bool(value: object) -> bool:
    return bool(value)


@RiskRuleRegistry.register
class DefaultRiskRule(RiskRule):
    name = "DEFAULT_RISK_RULE"
    version = "v1"
    enabled = True

    def __init__(self, config: DefaultRiskRuleConfig | None = None) -> None:
        self.config = config or DefaultRiskRuleConfig()

    def run(self, edge_decision: dict[str, Any]) -> RiskRuleResult:
        started = time.perf_counter()
        cfg = self.config

        edge_score = _num(edge_decision.get("edge_score"))
        validation_score = _num(edge_decision.get("validation_score"))
        ready_for_paper = _bool(edge_decision.get("ready_for_paper"))
        ready_for_live = _bool(edge_decision.get("ready_for_live"))
        ready_for_micro_live = _bool(edge_decision.get("ready_for_micro_live"))

        edge_ok = edge_score >= cfg.min_edge_score
        validation_ok = validation_score >= cfg.min_validation_score
        paper_ok = ready_for_paper
        live_block_ok = not ready_for_live and not ready_for_micro_live
        kill_switch_ok = cfg.kill_switch_enabled

        checks = {
            "edge_score": edge_ok,
            "validation_score": validation_ok,
            "ready_for_paper": paper_ok,
            "live_block": live_block_ok,
            "kill_switch": kill_switch_ok,
        }

        passed = all(checks.values())
        risk_score = 1.0 if passed else 0.0

        return RiskRuleResult(
            rule_name=self.name,
            rule_version=self.version,
            risk_score=risk_score,
            passed=passed,
            reason_code="RISK_PASS" if passed else "RISK_BLOCK",
            diagnostics=RiskRuleDiagnostics(
                input_values={
                    "edge_score": edge_score,
                    "validation_score": validation_score,
                    "ready_for_paper": float(ready_for_paper),
                    "ready_for_live": float(ready_for_live),
                    "ready_for_micro_live": float(ready_for_micro_live),
                },
                thresholds={
                    "min_edge_score": cfg.min_edge_score,
                    "min_validation_score": cfg.min_validation_score,
                    "max_risk_per_trade": cfg.max_risk_per_trade,
                    "exposure_limit": cfg.exposure_limit,
                },
                component_scores={k: float(v) for k, v in checks.items()},
                execution_time_ms=(time.perf_counter() - started) * 1000.0,
                details={},
            ),
        )
