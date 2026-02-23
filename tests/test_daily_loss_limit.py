import pytest
from risk.risk_engine import RiskEngine
from accounting.position_manager import PositionManager


def test_daily_loss_limit_block():

    pm = PositionManager(starting_cash=100_000)

    # эмулируем дневной убыток -8%
    pm.daily_realized_pnl = -8_000
    context = pm.get_context()

    risk = RiskEngine(max_daily_loss_pct=0.05)  # 5%

    class DummySignal:
        def __init__(self):
            self.symbol = "NG"
            self.qty = 1
            self.price = 100

    signal = DummySignal()

    approved = risk.evaluate(signal, context)

    assert approved is None