from risk.risk_engine import RiskEngine
from accounting.position_manager import PositionManager


class DummySignal:
    def __init__(self, symbol="NG", qty=1, price=1000, side="BUY"):
        self.symbol = symbol
        self.qty = qty
        self.price = price
        self.side = side


def test_correlation_block():
    risk = RiskEngine(
        correlation_matrix={
            "NG": {"BR": 0.9}
        }
    )

    pm = PositionManager(starting_cash=100_000)
    pm.positions["BR"].qty = 1
    pm.positions["BR"].avg_price = 40_000

    context = pm.get_context()

    signal = DummySignal(symbol="NG", qty=1, price=10_000)

    approved = risk.evaluate(signal, context)

    assert approved is None


def test_drawdown_guard():
    pm = PositionManager(starting_cash=100_000)
    pm.cash = 70_000  # 30% drawdown

    dd = pm.current_drawdown()

    assert dd < -0.2