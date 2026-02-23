from risk.risk_engine import RiskEngine
from accounting.position_manager import PositionManager


def test_risk_freeze_after_daily_limit():

    pm = PositionManager(starting_cash=100_000)

    pm.daily_realized_pnl = -10_000  # -10%
    context = pm.get_context()

    risk = RiskEngine(max_daily_loss_pct=0.05)

    class DummySignal:
        def __init__(self):
            self.symbol = "NG"
            self.qty = 1
            self.price = 100

    signal = DummySignal()

    # первый вызов — должен заблокировать и включить freeze
    approved = risk.evaluate(signal, context)
    assert approved is None
    assert risk.is_frozen is True

    # даже если уберём просадку — freeze остаётся
    pm.daily_realized_pnl = 0
    context = pm.get_context()

    approved = risk.evaluate(signal, context)
    assert approved is None