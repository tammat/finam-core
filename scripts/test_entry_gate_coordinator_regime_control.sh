#!/usr/bin/env bash
set -euo pipefail

export PYTHONPATH=src

python -m py_compile \
  src/finam_core/runtime/entry_gate_coordinator.py \
  src/finam_core/runtime/regime_runtime_control_service.py \
  src/finam_core/runtime/strategy_runtime_control_service.py \
  src/finam_core/runtime/trade_gate_service.py \
  src/finam_core/runtime/trend_gate_service.py

python - <<'PY'
from finam_core.runtime.entry_gate_coordinator import EntryGateCoordinator
from finam_core.runtime.trade_gate_service import TradeGateService
from finam_core.runtime.trend_gate_service import TrendGateService


class RuntimeAllowStub:
    def allow_paper(self, symbol: str, qty: float, strategy: str):
        return True, qty, "runtime_control_ok:stub"


class RuntimeBlockStub:
    def allow_paper(self, symbol: str, qty: float, strategy: str):
        return False, 0.0, "runtime_control_blocked:stub"


class RegimeAllowStub:
    def allow_regime(self, symbol: str, strategy: str, regime: str | None, qty: float):
        return True, qty, f"regime_control_ok:stub:{regime}"


class RegimeBlockStub:
    def allow_regime(self, symbol: str, strategy: str, regime: str | None, qty: float):
        return False, 0.0, f"regime_control_blocked:stub:{regime}"


def make(runtime, regime):
    return EntryGateCoordinator(
        trade_gate_service=TradeGateService(
            base_cooldown_sec=0,
            max_trades_per_hour=10,
            max_trades_per_symbol=10,
        ),
        runtime_control_service=runtime,
        trend_gate_service=TrendGateService(),
        regime_runtime_control_service=regime,
    )


# 1. Global runtime block должен остановить до regime-control.
c = make(RuntimeBlockStub(), RegimeAllowStub())
d = c.allow_entry(
    symbol="BR_CONT",
    strategy="BR_CONSERVATIVE_BREAKOUT",
    strategy_side="BUY",
    expected_side="BUY",
    qty=1.0,
    price=108.5,
    atr=0.2,
    regime="trend_up_high_vol",
)

assert d.allowed is False, d
assert d.gate == "runtime_control", d


# 2. Если global runtime OK, regime-control может заблокировать.
c = make(RuntimeAllowStub(), RegimeBlockStub())
d = c.allow_entry(
    symbol="BR_CONT",
    strategy="BR_CONSERVATIVE_BREAKOUT",
    strategy_side="BUY",
    expected_side="BUY",
    qty=1.0,
    price=108.5,
    atr=0.2,
    regime="trend_up_high_vol",
)

assert d.allowed is False, d
assert d.gate == "regime_runtime_control", d
assert "trend_up_high_vol" in d.reason, d


# 3. Полный allow path.
c = make(RuntimeAllowStub(), RegimeAllowStub())
d = c.allow_entry(
    symbol="BR_CONT",
    strategy="BR_CONSERVATIVE_BREAKOUT",
    strategy_side="BUY",
    expected_side="BUY",
    qty=1.0,
    price=108.5,
    atr=0.2,
    regime="breakout",
)

assert d.allowed is True, d
assert d.gate == "allow", d
assert d.qty == 1.0, d
assert "regime_control_ok" in d.reason, d

print("OK: EntryGateCoordinator supports regime-level runtime control")
PY
