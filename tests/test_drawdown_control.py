import pytest
from risk.risk_engine import RiskEngine
from accounting.position_manager import PositionManager


def test_max_drawdown_block():

    pm = PositionManager(starting_cash=100_000)

    # эмулируем просадку
    pm.realized_pnl = -20_000  # -20%
    context = pm.get_context()

    risk = RiskEngine(max_drawdown_pct=0.1)  # 10%

    class DummySignal:
        def __init__(self):
            self.symbol = "NG"
            self.qty = 1
            self.price = 100

    signal = DummySignal()

    approved = risk.evaluate(signal, context)

    assert approved is None