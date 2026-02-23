def test_volatility_sizing():
    from risk.sizing_engine import SizingEngine

    class DummyContext:
        equity = 100_000

    class DummySignal:
        def __init__(self):
            self.price = 100
            self.qty = 0
            self.atr = 5

    sizing = SizingEngine(
        risk_per_trade=0.02,
        mode="volatility",
        atr_multiplier=2
    )

    signal = DummySignal()
    context = DummyContext()

    sized = sizing.size(signal, context)

    # risk capital = 2000
    # stop_distance = 5 * 2 = 10
    # qty = 2000 / 10 = 200
    assert round(sized.qty, 2) == 200