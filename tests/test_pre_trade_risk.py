from risk.pre_trade_risk import PreTradeRiskEngine, RiskConfig
from accounting.portfolio_manager import PortfolioState


def main():
    config = RiskConfig(
        max_risk_per_trade=100_000,
        max_total_exposure=500_000,
        daily_loss_limit=50_000,
        max_portfolio_heat=2.0,
    )
    engine = PreTradeRiskEngine(config)

    state = PortfolioState(
        cash=10000.0,
        equity=10000.0,
        realized_pnl=0.0,
        unrealized_pnl=0.0,
        exposure=1000.0,
        drawdown=0.0,
    )

    # Valid trade
    allowed, reason = engine.validate(state, "NG", "BUY", 1, 500)
    assert allowed

    # Risk per trade (exceeds 10000 limit)
    allowed, reason = engine.validate(state, "NG", "BUY", 1, 20000)
    assert not allowed
    assert reason == "MAX_RISK_PER_TRADE_EXCEEDED"

    # Exposure breach
    allowed, reason = engine.validate(state, "NG", "BUY", 10, 500)
    assert not allowed
    assert reason == "MAX_TOTAL_EXPOSURE_EXCEEDED"

    # Daily loss breach
    state.realized_pnl = -3000
    allowed, reason = engine.validate(state, "NG", "BUY", 1, 100)
    assert not allowed
    assert reason == "DAILY_LOSS_LIMIT_EXCEEDED"

    # Kill switch
    engine.enable_kill_switch()
    allowed, reason = engine.validate(state, "NG", "BUY", 1, 100)
    assert not allowed
    assert reason == "KILL_SWITCH_ACTIVE"

    engine.disable_kill_switch()

    # Negative cash test
    state.cash = 100
    allowed, reason = engine.validate(state, "NG", "BUY", 1, 200)
    assert not allowed
    assert reason == "NEGATIVE_CASH"
    print("ok: pre-trade risk works")

import os

def test_risk_validate_records_latency(monkeypatch):
    monkeypatch.setenv("RISK_LATENCY", "1")

    from risk.pre_trade_risk import PreTradeRiskEngine, RiskConfig
    from accounting.position_manager import PositionManager

    engine = PreTradeRiskEngine(RiskConfig(
        max_risk_per_trade=1_000_000,
        max_total_exposure=1_000_000,
        daily_loss_limit=1_000_000,
        max_portfolio_heat=10.0,
    ))

    pm = PositionManager(starting_cash=100_000)
    ctx = pm.get_context()

    allowed, reason = engine.validate(ctx, "SI", "BUY", 1, 100)

    assert engine.latency is not None
    assert engine.latency.count >= 1
def test_latency_percentiles(monkeypatch):
    monkeypatch.setenv("RISK_LATENCY", "1")

    from risk.pre_trade_risk import PreTradeRiskEngine, RiskConfig
    from accounting.position_manager import PositionManager

    engine = PreTradeRiskEngine(RiskConfig(
        max_risk_per_trade=1_000_000,
        max_total_exposure=1_000_000,
        daily_loss_limit=1_000_000,
        max_portfolio_heat=10.0,
    ))

    pm = PositionManager(starting_cash=100_000)
    ctx = pm.get_context()

    for _ in range(100):
        engine.validate(ctx, "SI", "BUY", 1, 100)

    snap = engine.latency.snapshot()

    assert snap["count"] >= 100
    assert snap["p95_ms"] >= 0.0
    assert snap["p99_ms"] >= snap["p95_ms"]
if __name__ == "__main__":
    raise SystemExit(main())