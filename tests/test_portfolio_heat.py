def test_portfolio_heat_block():

    from risk.pre_trade_risk import PreTradeRiskEngine, RiskConfig
    from accounting.position_manager import PositionManager

    # ---- SETUP ----
    config = RiskConfig(
        max_risk_per_trade=1_000_000,
        max_total_exposure=1_000_000,
        daily_loss_limit=1_000_000,
        max_portfolio_heat=0.01,  # 1%
    )

    engine = PreTradeRiskEngine(config)

    pm = PositionManager(starting_cash=100_000)

    # existing position: 10 * 100 = 1000 exposure
    pm.positions["NG"].qty = 10
    pm.positions["NG"].avg_price = 100
    pm.positions["NG"].mark_price = 100

    # equity ≈ 100_000
    # equity ≈ 100_000
    portfolio_state = pm.get_context()

    print("equity:", getattr(portfolio_state, "equity", None))
    print("gross:", engine._calculate_gross_exposure(portfolio_state))

    # New trade...
    allowed, reason = engine.validate(
        portfolio_state=portfolio_state,
        symbol="BR",
        side="BUY",
        qty=10,
        price=100,
    )
    # New trade: 10 * 100 = 1000 additional exposure
    allowed, reason = engine.validate(
        portfolio_state=portfolio_state,
        symbol="BR",
        side="BUY",
        qty=10,
        price=100,
    )

    assert allowed is False
    assert reason == "MAX_PORTFOLIO_HEAT_EXCEEDED"