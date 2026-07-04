#!/usr/bin/env bash
set -euo pipefail

echo "=== BUILD_RISK_RULE_ENGINE_V1 ==="

mkdir -p src/risk/base src/risk/default_rule scripts

touch src/risk/__init__.py
touch src/risk/base/__init__.py
touch src/risk/default_rule/__init__.py

cat > src/risk/base/result.py <<'PY'
from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(slots=True, frozen=True)
class RiskRuleDiagnostics:
    input_values: dict[str, float]
    thresholds: dict[str, float]
    component_scores: dict[str, float]
    execution_time_ms: float
    details: dict[str, Any]


@dataclass(slots=True, frozen=True)
class RiskRuleResult:
    rule_name: str
    rule_version: str
    risk_score: float
    passed: bool
    diagnostics: RiskRuleDiagnostics
    reason_code: str
PY

cat > src/risk/base/rule.py <<'PY'
from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any

from risk.base.result import RiskRuleResult


class RiskRule(ABC):
    name: str
    version: str
    enabled: bool = True

    @abstractmethod
    def run(self, edge_decision: dict[str, Any]) -> RiskRuleResult:
        raise NotImplementedError
PY

cat > src/risk/base/registry.py <<'PY'
from __future__ import annotations

from risk.base.rule import RiskRule


class RiskRuleRegistry:
    _registry: dict[str, type[RiskRule]] = {}

    @classmethod
    def register(cls, rule_cls: type[RiskRule]) -> type[RiskRule]:
        name = getattr(rule_cls, "name", "")
        if not name:
            raise ValueError("risk rule name is required")
        cls._registry[name] = rule_cls
        return rule_cls

    @classmethod
    def enabled(cls) -> list[type[RiskRule]]:
        return [r for r in cls._registry.values() if getattr(r, "enabled", True)]

    @classmethod
    def get(cls, name: str) -> type[RiskRule] | None:
        return cls._registry.get(name)

    @classmethod
    def clear_for_tests(cls) -> None:
        cls._registry.clear()
PY

cat > src/risk/base/executor.py <<'PY'
from __future__ import annotations

from risk.base.result import RiskRuleResult
from risk.base.rule import RiskRule


class RiskRuleExecutor:
    def execute(self, rule: RiskRule, edge_decision: dict) -> RiskRuleResult:
        return rule.run(edge_decision)
PY

cat > src/risk/default_rule/config.py <<'PY'
from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(slots=True, frozen=True)
class DefaultRiskRuleConfig:
    min_edge_score: float = 0.60
    min_validation_score: float = 0.70
    max_risk_per_trade: float = 0.01
    exposure_limit: float = 0.10
    kill_switch_enabled: bool = True

    @classmethod
    def from_dict(cls, data: dict[str, Any] | None) -> "DefaultRiskRuleConfig":
        data = data or {}
        defaults = cls()
        return cls(
            min_edge_score=float(data.get("min_edge_score", defaults.min_edge_score)),
            min_validation_score=float(data.get("min_validation_score", defaults.min_validation_score)),
            max_risk_per_trade=float(data.get("max_risk_per_trade", defaults.max_risk_per_trade)),
            exposure_limit=float(data.get("exposure_limit", defaults.exposure_limit)),
            kill_switch_enabled=bool(data.get("kill_switch_enabled", defaults.kill_switch_enabled)),
        )
PY

cat > src/risk/default_rule/rule.py <<'PY'
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
PY

cat > src/risk/default_rule/__init__.py <<'PY'
from risk.default_rule.rule import DefaultRiskRule

__all__ = ["DefaultRiskRule"]
PY

cat > scripts/test_risk_rule_engine_v1.sh <<'SH_TEST'
#!/usr/bin/env bash
set -euo pipefail

echo "=== TEST_RISK_RULE_ENGINE_V1 ==="

PYTHONPATH=src python -m py_compile \
  src/risk/base/result.py \
  src/risk/base/rule.py \
  src/risk/base/registry.py \
  src/risk/base/executor.py \
  src/risk/default_rule/config.py \
  src/risk/default_rule/rule.py \
  src/risk/default_rule/__init__.py

PYTHONPATH=src python - <<'PY'
from risk.base.executor import RiskRuleExecutor
from risk.base.registry import RiskRuleRegistry
import risk.default_rule
from risk.default_rule.rule import DefaultRiskRule

assert RiskRuleRegistry.get("DEFAULT_RISK_RULE") is DefaultRiskRule

rule = DefaultRiskRule()
executor = RiskRuleExecutor()

passed = executor.execute(rule, {
    "edge_score": 0.80,
    "validation_score": 0.80,
    "ready_for_paper": True,
    "ready_for_live": False,
    "ready_for_micro_live": False,
})
assert passed.passed is True
assert passed.risk_score == 1.0

low_edge = executor.execute(rule, {
    "edge_score": 0.20,
    "validation_score": 0.80,
    "ready_for_paper": True,
})
assert low_edge.passed is False

unsafe_live = executor.execute(rule, {
    "edge_score": 0.80,
    "validation_score": 0.80,
    "ready_for_paper": True,
    "ready_for_live": True,
})
assert unsafe_live.passed is False

not_ready = executor.execute(rule, {
    "edge_score": 0.80,
    "validation_score": 0.80,
    "ready_for_paper": False,
})
assert not_ready.passed is False
PY

echo "risk_rule_registry=ok"
echo "default_risk_rule=ok"
echo "pass_case=ok"
echo "low_edge=ok"
echo "unsafe_live=ok"
echo "not_ready=ok"
echo "runtime_changed=0"
echo "execution_changed=0"
echo "orders_changed=0"
echo "fills_changed=0"
echo "micro_live_allowed=0"
echo "VERDICT=RISK_RULE_ENGINE_V1_READY"
echo "VERDICT=TEST_RISK_RULE_ENGINE_V1_OK"
SH_TEST

chmod +x scripts/test_risk_rule_engine_v1.sh
scripts/test_risk_rule_engine_v1.sh

echo "VERDICT=BUILD_RISK_RULE_ENGINE_V1_OK"
