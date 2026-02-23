from risk.pre_trade_risk import PreTradeRiskEngine, RiskConfig
from accounting.portfolio_manager import PortfolioState


def main():

    config = RiskConfig(
        max_risk_per_trade=10000.0,  # high enough so exposure rule can trigger
        max_total_exposure=5000.0,
        daily_loss_limit=2000.0,
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
    allowed, reason = engine.validate(state, "BUY", 1, 500)
    assert allowed

    # Risk per trade (exceeds 10000 limit)
    allowed, reason = engine.validate(state, "BUY", 1, 20000)
    assert not allowed
    assert reason == "MAX_RISK_PER_TRADE_EXCEEDED"

    # Exposure breach
    allowed, reason = engine.validate(state, "BUY", 10, 500)
    assert not allowed
    assert reason == "MAX_TOTAL_EXPOSURE_EXCEEDED"

    # Daily loss breach
    state.realized_pnl = -3000
    allowed, reason = engine.validate(state, "BUY", 1, 100)
    assert not allowed
    assert reason == "DAILY_LOSS_LIMIT_EXCEEDED"

    # Kill switch
    engine.enable_kill_switch()
    allowed, reason = engine.validate(state, "BUY", 1, 100)
    assert not allowed
    assert reason == "KILL_SWITCH_ACTIVE"

    engine.disable_kill_switch()

    # Negative cash test
    state.cash = 100
    allowed, reason = engine.validate(state, "BUY", 1, 200)
    assert not allowed
    assert reason == "NEGATIVE_CASH"
    print("ok: pre-trade risk works")


if __name__ == "__main__":
    raise SystemExit(main())