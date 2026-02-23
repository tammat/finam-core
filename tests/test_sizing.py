def test_fixed_risk_sizing():

    from risk.sizing_engine import SizingEngine

    class DummyContext:
        equity = 100_000

    class DummySignal:
        def __init__(self):
            self.price = 100
            self.qty = 0

    sizing = SizingEngine(risk_per_trade=0.02)

    signal = DummySignal()
    context = DummyContext()

    sized = sizing.size(signal, context)

    assert round(sized.qty, 2) == 20.0