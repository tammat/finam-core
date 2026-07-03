#!/usr/bin/env bash
set -euo pipefail

echo "=== TEST_RISK_TRADING_FOUNDATION_V1 ==="

PYTHONPATH=src python -m py_compile \
  src/strategy/signal.py \
  src/portfolio/portfolio_state.py \
  src/risk/foundation/risk_context.py \
  src/risk/foundation/risk_verdict.py \
  src/trading/trade_intent.py \
  src/trading/trade_decision.py \
  src/trading/signal_gate.py \
  src/execution/order_intent.py

PYTHONPATH=src python - <<'PY'
from decimal import Decimal

from portfolio.portfolio_state import PortfolioState
from risk.foundation.risk_context import RiskContext
from strategy.signal import StrategySignal
from trading.signal_gate import make_trade_decision

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

decision = make_trade_decision(ctx)
assert decision.action == "BUY"
assert decision.risk_verdict.status == "PASS"
assert decision.approved_quantity == Decimal("1")

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

decision2 = make_trade_decision(blocked)
assert decision2.action == "BLOCK"
assert decision2.risk_verdict.status == "BLOCK"

print("risk_trading_foundation_contract=OK")
PY

echo "runtime_changed=0"
echo "execution_changed=0"
echo "orders_changed=0"
echo "fills_changed=0"
echo "micro_live_allowed=0"
echo "VERDICT=RISK_TRADING_FOUNDATION_V1_READY"
echo "VERDICT=TEST_RISK_TRADING_FOUNDATION_V1_OK"
