from analytics.equity_tracker import EquityTracker
from analytics.trade_log import TradeRecord
from datetime import datetime


def test_equity_updates():
    tracker = EquityTracker(initial_equity=1000)

    trade = TradeRecord(
        timestamp=datetime.now(),
        symbol="SI",
        side="BUY",
        entry_price=100,
        exit_price=110,
        quantity=1,
    )

    tracker.apply_trade(trade)

    assert tracker.equity == 1010