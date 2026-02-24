import uuid
from datetime import datetime, timezone

from accounting.position_manager import PositionManager
from core.events import FillEvent

def make_fill(side, qty, price):
    return FillEvent(
        fill_id=str(uuid.uuid4()),
        order_id=str(uuid.uuid4()),
        symbol="NG",
        side=side,
        qty=qty,
        price=price,
        commission=0.0,
        timestamp=datetime.now(timezone.utc),
    )


def test_realized_pnl_calculation():
    pm = PositionManager(starting_cash=100_000)

    # Buy 1 @ 100
    pm.apply_fill(make_fill("BUY", 1, 100))

    # Sell 1 @ 110
    pm.apply_fill(make_fill("SELL", 1, 110))

    pos = pm.positions["NG"]

    assert pos.qty == 0
    assert pos.realized_pnl == 10


def test_unrealized_pnl_mark_to_market():
    pm = PositionManager(starting_cash=100_000)

    pm.apply_fill(make_fill("BUY", 1, 100))

    pm.update_market_price("NG", 120)

    context = pm.get_context()

    assert context.equity == 100_000 - 100 + 120