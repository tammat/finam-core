from risk.risk_engine import RiskEngine
from accounting.position_manager import PositionManager


class DummySignal:
    def __init__(self, qty, price, side="BUY", symbol="NG"):
        self.qty = qty
        self.price = price
        self.side = side
        self.symbol = symbol


def test_position_size_limit():
    pm = PositionManager(starting_cash=100_000)
    context = pm.get_context()

    risk = RiskEngine(max_position_pct=0.1)

    signal = DummySignal(qty=10, price=2_000)  # 20k notional

    approved = risk.evaluate(signal, context)

    assert approved is None


def test_gross_exposure_limit():
    pm = PositionManager(starting_cash=100_000)
    pm.positions["NG"].qty = 1
    pm.positions["NG"].avg_price = 40_000

    context = pm.get_context()

    risk = RiskEngine(max_gross_exposure_pct=0.3)

    signal = DummySignal(qty=1, price=40_000)

    approved = risk.evaluate(signal, context)

    assert approved is None