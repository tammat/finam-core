def test_volatility_sizing():
    from risk.sizing_engine import SizingEngine

    class DummyContext:
        equity = 100_000
        drawdown = 0.0

    class DummySignal:
        def __init__(self):
            self.price = 100
            self.atr = 5

    sizing = SizingEngine(
        risk_pct=0.02,
        atr_multiplier=2.0,
        max_position_pct=1.0
    )

    signal = DummySignal()
    context = DummyContext()

    qty = sizing.size(signal, context)

    # risk capital = 100_000 * 0.02 = 2000
    # stop_distance = 5 * 2 = 10
    # qty = 2000 / 10 = 200
    assert round(qty, 2) == 200.0