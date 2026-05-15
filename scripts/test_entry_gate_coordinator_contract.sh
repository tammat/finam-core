#!/usr/bin/env bash
set -euo pipefail

export PYTHONPATH=src

python -m py_compile \
  src/finam_core/runtime/entry_gate_coordinator.py \
  src/finam_core/runtime/trade_gate_service.py \
  src/finam_core/runtime/trend_gate_service.py \
  src/finam_core/runtime/strategy_runtime_control_service.py

python - <<'PY'
from finam_core.runtime.entry_gate_coordinator import EntryGateCoordinator
from finam_core.runtime.trade_gate_service import TradeGateService
from finam_core.runtime.trend_gate_service import TrendGateService


class RuntimeControlAllowStub:
    def allow_paper(self, symbol: str, qty: float, strategy: str):
        return True, qty, "runtime_control_ok:stub"


class RuntimeControlBlockStub:
    def allow_paper(self, symbol: str, qty: float, strategy: str):
        return False, 0.0, "runtime_control_blocked:stub"


def make_coordinator(runtime):
    return EntryGateCoordinator(
        trade_gate_service=TradeGateService(
            base_cooldown_sec=0,
            max_trades_per_hour=10,
            max_trades_per_symbol=10,
        ),
        runtime_control_service=runtime,
        trend_gate_service=TrendGateService(),
    )


# 1. Полный allow path.
c = make_coordinator(RuntimeControlAllowStub())
d = c.allow_entry(
    symbol="BRM6@RTSX",
    strategy="BR_CONSERVATIVE_BREAKOUT",
    strategy_side="BUY",
    expected_side="BUY",
    qty=1.0,
    price=108.5,
    atr=0.2,
)

assert d.allowed is True, d
assert d.qty == 1.0, d
assert d.gate == "allow", d


# 2. Trend block должен сработать до runtime-control.
c = make_coordinator(RuntimeControlAllowStub())
d = c.allow_entry(
    symbol="BRM6@RTSX",
    strategy="BR_CONSERVATIVE_BREAKOUT",
    strategy_side="BUY",
    expected_side="SELL",
    qty=1.0,
    price=108.5,
    atr=0.2,
)

assert d.allowed is False, d
assert d.gate == "trend", d
assert "trend_block" in d.reason, d


# 3. Runtime-control block.
c = make_coordinator(RuntimeControlBlockStub())
d = c.allow_entry(
    symbol="BRM6@RTSX",
    strategy="BR_CONSERVATIVE_BREAKOUT",
    strategy_side="BUY",
    expected_side="BUY",
    qty=1.0,
    price=108.5,
    atr=0.2,
)

assert d.allowed is False, d
assert d.gate == "runtime_control", d
assert "runtime_control_blocked" in d.reason, d

print("OK: EntryGateCoordinator contract is valid")
PY
