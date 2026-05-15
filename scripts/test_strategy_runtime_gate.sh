#!/usr/bin/env bash
set -euo pipefail

export PYTHONPATH=src

python -m py_compile src/finam_core/execution/strategy_runtime_gate.py

python - <<'PY'
from dataclasses import dataclass

from finam_core.execution.strategy_runtime_gate import StrategyRuntimeGate


@dataclass
class RuntimeDecision:
    status: str
    allow_trade: bool
    watch_only: bool
    risk_multiplier: float
    reason: str


class Repo:
    def __init__(self, decision):
        self.decision = decision

    def get_decision(self, symbol, strategy):
        assert symbol == "BRM6@RTSX"
        assert strategy == "BR_CONSERVATIVE_BREAKOUT_M5"
        return self.decision


intent = {
    "symbol": "BRM6@RTSX",
    "strategy": "BR_CONSERVATIVE_BREAKOUT_M5",
    "qty": 2,
}

allowed_gate = StrategyRuntimeGate(Repo(RuntimeDecision(
    status="HEALTHY",
    allow_trade=True,
    watch_only=False,
    risk_multiplier=1.2,
    reason="Положительное матожидание",
)))

allowed = allowed_gate.evaluate(intent)
assert allowed.allowed is True
assert allowed.adjusted_qty == 2.4
assert allowed.risk_multiplier == 1.2

blocked_gate = StrategyRuntimeGate(Repo(RuntimeDecision(
    status="BLOCKED",
    allow_trade=False,
    watch_only=True,
    risk_multiplier=0.0,
    reason="Отрицательное матожидание",
)))

blocked = blocked_gate.evaluate(intent)
assert blocked.allowed is False
assert blocked.adjusted_qty == 0.0
assert blocked.watch_only is True
assert blocked.status == "BLOCKED"

no_repo = StrategyRuntimeGate(None).evaluate(intent)
assert no_repo.allowed is True
assert no_repo.adjusted_qty == 2.0
assert no_repo.status == "NO_REPOSITORY"

print("OK: runtime-gate стратегий работает")
PY
