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
