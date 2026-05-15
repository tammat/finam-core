#!/usr/bin/env bash
set -euo pipefail

export PYTHONPATH=src

python -m py_compile \
  src/finam_core/runtime/entry_gate_coordinator.py

python - <<'PY'
from finam_core.runtime.trade_gate_service import TradeGateService
from finam_core.runtime.entry_gate_coordinator import EntryGateCoordinator


class RuntimeStub:
    def allow_paper(self, symbol, qty, strategy):
        return True, qty, "runtime_ok"


trade_gate = TradeGateService(
    base_cooldown_sec=1000,
    max_trades_per_hour=1,
    max_trades_per_symbol=1,
)

coordinator = EntryGateCoordinator(
    trade_gate_service=trade_gate,
    runtime_control_service=RuntimeStub(),
)

d1 = coordinator.allow_entry(
    symbol="BRM6@RTSX",
    strategy="BR_CONSERVATIVE_BREAKOUT",
    qty=1.0,
    price=100.0,
    atr=1.0,
)

assert d1.allowed is True, d1

d2 = coordinator.allow_entry(
    symbol="BRM6@RTSX",
    strategy="BR_CONSERVATIVE_BREAKOUT",
    qty=1.0,
    price=100.0,
    atr=1.0,
)

assert d2.allowed is False, d2
assert d2.gate == "trade_cooldown"

print("OK: EntryGateCoordinator works")
PY
