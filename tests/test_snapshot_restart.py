from accounting.position_manager import PositionManager
from storage.snapshot_repository import SnapshotRepository


def test_snapshot_restart():

    pm = PositionManager(starting_cash=100_000)

    # simulate state
    pm.positions["NG"].qty = 5
    pm.positions["NG"].avg_price = 100
    pm.positions["NG"].mark_price = 110
    pm.realized_pnl = 500

    repo = SnapshotRepository("data/test_snapshot.json")

    snapshot = pm.get_snapshot()
    repo.save(snapshot)

    # restart simulation
    pm2 = PositionManager(starting_cash=0)

    loaded = repo.load()
    pm2.load_snapshot(loaded)

    assert pm2.cash == pm.cash
    assert pm2.realized_pnl == pm.realized_pnl
    assert pm2.positions["NG"].qty == pm.positions["NG"].qty
    assert pm2.positions["NG"].avg_price == pm.positions["NG"].avg_price
    assert pm2.positions["NG"].mark_price == pm.positions["NG"].mark_price