#!/usr/bin/env bash
set -euo pipefail

echo "=== TEST_RISK_ENGINE_FOUNDATION_V1 ==="

PYTHONPATH=src python -m py_compile \
  src/risk/foundation/risk_module.py \
  src/risk/foundation/risk_engine.py \
  src/risk/foundation/risk_context.py \
  src/risk/foundation/risk_verdict.py \
  src/portfolio/portfolio_state.py \
  src/strategy/signal.py

PYTHONPATH=src python - <<'PY'
from decimal import Decimal

from portfolio.portfolio_state import PortfolioState
from risk.foundation.risk_context import RiskContext
from risk.foundation.risk_engine import RiskEngine
from strategy.signal import StrategySignal

signal = StrategySignal(
    signal_id="s1",
    symbol="LKOH@MISX",
    timeframe="M5",
    strategy="TEST_EDGE",
    side="BUY",
    signal_strength=Decimal("0.8"),
)

portfolio = PortfolioState(
    equity=Decimal("100000"),
    free_cash=Decimal("90000"),
    gross_exposure=Decimal("10000"),
    symbol_exposure=Decimal("0"),
    open_positions=1,
    daily_pnl=Decimal("0"),
    daily_drawdown=Decimal("0"),
)

ctx = RiskContext(
    signal=signal,
    portfolio=portfolio,
    asset_class="EQUITY",
    requested_quantity=Decimal("1"),
    max_risk_per_trade=Decimal("1000"),
    daily_loss_limit=Decimal("3000"),
    exposure_limit=Decimal("50000"),
    kill_switch_enabled=False,
)

engine = RiskEngine()
result = engine.evaluate(ctx)

assert result.verdict.status == "PASS"
assert result.verdict.risk_score == 0
assert len(result.module_results) == 5

blocked = RiskContext(
    signal=signal,
    portfolio=portfolio,
    asset_class="EQUITY",
    requested_quantity=Decimal("1"),
    max_risk_per_trade=Decimal("1000"),
    daily_loss_limit=Decimal("3000"),
    exposure_limit=Decimal("50000"),
    kill_switch_enabled=True,
)

blocked_result = engine.evaluate(blocked)
assert blocked_result.verdict.status == "BLOCK"
assert "kill_switch_enabled" in blocked_result.verdict.reasons

print("risk_engine_foundation_contract=OK")
print("modules=5")
print("pass_case=OK")
print("block_case=OK")
PY

echo "runtime_changed=0"
echo "execution_changed=0"
echo "orders_changed=0"
echo "fills_changed=0"
echo "micro_live_allowed=0"
echo "VERDICT=RISK_ENGINE_FOUNDATION_V1_READY"
echo "VERDICT=TEST_RISK_ENGINE_FOUNDATION_V1_OK"
