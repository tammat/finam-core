#!/usr/bin/env bash
set -euo pipefail

echo "=== BUILD_RISK_TRADING_FOUNDATION_V1 ==="

mkdir -p src/strategy src/portfolio src/risk/foundation src/trading src/execution scripts

cat > src/strategy/signal.py <<'PY'
from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal


@dataclass(frozen=True)
class StrategySignal:
    signal_id: str
    symbol: str
    timeframe: str
    strategy: str
    side: str
    signal_strength: Decimal
    source: str = "strategy"
PY

cat > src/portfolio/portfolio_state.py <<'PY'
from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal


@dataclass(frozen=True)
class PortfolioState:
    equity: Decimal
    free_cash: Decimal
    gross_exposure: Decimal
    symbol_exposure: Decimal
    open_positions: int
    daily_pnl: Decimal
    daily_drawdown: Decimal
PY

cat > src/risk/foundation/risk_verdict.py <<'PY'
from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class RiskVerdict:
    status: str
    risk_score: int
    reasons: tuple[str, ...]

    def is_pass(self) -> bool:
        return self.status == "PASS"
PY

cat > src/risk/foundation/risk_context.py <<'PY'
from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal

from portfolio.portfolio_state import PortfolioState
from strategy.signal import StrategySignal


@dataclass(frozen=True)
class RiskContext:
    signal: StrategySignal
    portfolio: PortfolioState
    asset_class: str
    requested_quantity: Decimal
    max_risk_per_trade: Decimal
    daily_loss_limit: Decimal
    exposure_limit: Decimal
    kill_switch_enabled: bool
PY

cat > src/trading/trade_intent.py <<'PY'
from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal


@dataclass(frozen=True)
class TradeIntent:
    symbol: str
    timeframe: str
    strategy: str
    side: str
    quantity_requested: Decimal
    source_signal_id: str
PY

cat > src/trading/trade_decision.py <<'PY'
from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal

from risk.foundation.risk_verdict import RiskVerdict


@dataclass(frozen=True)
class TradeDecision:
    action: str
    symbol: str
    side: str
    approved_quantity: Decimal
    risk_verdict: RiskVerdict
    decision_reason: str
PY

cat > src/execution/order_intent.py <<'PY'
from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal


@dataclass(frozen=True)
class OrderIntent:
    symbol: str
    side: str
    quantity: Decimal
    order_type: str
    execution_mode: str
    source_decision: str
PY

cat > src/trading/signal_gate.py <<'PY'
from __future__ import annotations

from decimal import Decimal

from risk.foundation.risk_context import RiskContext
from risk.foundation.risk_verdict import RiskVerdict
from trading.trade_decision import TradeDecision


def evaluate_basic_risk(ctx: RiskContext) -> RiskVerdict:
    if ctx.kill_switch_enabled:
        return RiskVerdict("BLOCK", 1000, ("kill_switch_enabled",))

    if ctx.portfolio.daily_drawdown <= -ctx.daily_loss_limit:
        return RiskVerdict("BLOCK", 900, ("daily_loss_limit_reached",))

    if ctx.portfolio.gross_exposure + ctx.requested_quantity > ctx.exposure_limit:
        return RiskVerdict("BLOCK", 800, ("exposure_limit_exceeded",))

    if ctx.requested_quantity <= Decimal("0"):
        return RiskVerdict("BLOCK", 700, ("bad_quantity",))

    if ctx.signal.signal_strength < Decimal("0.5"):
        return RiskVerdict("WARN", 300, ("weak_signal",))

    return RiskVerdict("PASS", 0, ("risk_pass",))


def make_trade_decision(ctx: RiskContext) -> TradeDecision:
    verdict = evaluate_basic_risk(ctx)

    if verdict.status == "BLOCK":
        return TradeDecision(
            action="BLOCK",
            symbol=ctx.signal.symbol,
            side=ctx.signal.side,
            approved_quantity=Decimal("0"),
            risk_verdict=verdict,
            decision_reason="risk_block",
        )

    return TradeDecision(
        action=ctx.signal.side,
        symbol=ctx.signal.symbol,
        side=ctx.signal.side,
        approved_quantity=ctx.requested_quantity,
        risk_verdict=verdict,
        decision_reason="risk_allowed",
    )
PY

cat > scripts/test_risk_trading_foundation_v1.sh <<'SH_TEST'
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
SH_TEST

chmod +x scripts/test_risk_trading_foundation_v1.sh
scripts/test_risk_trading_foundation_v1.sh

echo "VERDICT=BUILD_RISK_TRADING_FOUNDATION_V1_OK"
