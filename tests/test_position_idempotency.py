import uuid
from datetime import datetime, timezone

from accounting.position_manager import PositionManager
from core.events import FillEvent

def make_fill(fill_id):
    return FillEvent(
        fill_id=fill_id,
        order_id=str(uuid.uuid4()),
        symbol="NG",
        side="BUY",
        qty=1,
        price=100,
        commission=1.0,
        timestamp=datetime.now(timezone.utc),
    )


def test_fill_idempotency():
    pm = PositionManager(starting_cash=100_000)

    fill = make_fill("X1")

    pm.apply_fill(fill)
    pm.apply_fill(fill)  # duplicate

    assert len(pm.processed_fills) == 1
    assert pm.positions["NG"].qty == 1