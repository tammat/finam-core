def test_portfolio_heat_block():

    from risk.risk_engine import RiskEngine
    from accounting.position_manager import PositionManager

    pm = PositionManager(starting_cash=100_000)

    # existing position
    pm.positions["NG"].qty = 10
    pm.positions["NG"].avg_price = 100

    context = pm.get_context()

    risk = RiskEngine(max_portfolio_heat=0.05)

    class DummySignal:
        def __init__(self):
            self.symbol = "BR"
            self.qty = 10
            self.price = 100
            self.atr = 100  # high risk

    signal = DummySignal()

    approved = risk.evaluate(signal, context)

    assert approved is None