#!/usr/bin/env bash
set -euo pipefail

export PYTHONPATH=src

python -m py_compile \
  src/finam_core/control/adaptive_strategy_controller.py \
  src/scripts/run_strategy_performance_monitor.py

python - <<'PY'
from finam_core.control.adaptive_strategy_controller import AdaptiveStrategyController, StrategyRuntimeDecision

class FakeController(AdaptiveStrategyController):
    def __init__(self, status):
        self.status = status

    def get_decision(self, symbol, strategy="default"):
        return StrategyRuntimeDecision(
            symbol=symbol,
            strategy=strategy,
            status=self.status,
            allow_trade=False,
            watch_only=True,
            risk_multiplier=0.0,
            reason="test",
        )

c = FakeController("BLOCKED")
assert c.apply_recovery_hysteresis(
    symbol="PLZL@MISX",
    strategy="default",
    candidate_status="HEALTHY",
    candidate_reason="stable_positive_expectancy",
)[0] == "WATCH"

c = FakeController("DEGRADED")
assert c.apply_recovery_hysteresis(
    symbol="GAZP@MISX",
    strategy="default",
    candidate_status="HEALTHY",
    candidate_reason="stable_positive_expectancy",
)[0] == "WATCH"

c = FakeController("WATCH")
assert c.apply_recovery_hysteresis(
    symbol="BRM6@RTSX",
    strategy="default",
    candidate_status="HEALTHY",
    candidate_reason="stable_positive_expectancy",
)[0] == "HEALTHY"

print("OK: strategy recovery hysteresis rules passed")
PY
