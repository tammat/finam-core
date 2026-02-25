from analytics.metrics import win_rate, profit_factor
from analytics.trade_log import TradeRecord
from datetime import datetime


def test_win_rate():
    trades = [
        TradeRecord(datetime.now(), "SI", "BUY", 100, 110, 1),
        TradeRecord(datetime.now(), "SI", "BUY", 100, 90, 1),
    ]

    assert win_rate(trades) == 0.5