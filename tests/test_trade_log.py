from analytics.trade_log import TradeRecord
from datetime import datetime


def test_trade_pnl_buy():
    trade = TradeRecord(
        timestamp=datetime.now(),
        symbol="SI",
        side="BUY",
        entry_price=100,
        exit_price=110,
        quantity=1,
    )

    assert trade.pnl == 10


def test_trade_pnl_sell():
    trade = TradeRecord(
        timestamp=datetime.now(),
        symbol="SI",
        side="SELL",
        entry_price=100,
        exit_price=90,
        quantity=1,
    )

    assert trade.pnl == 10