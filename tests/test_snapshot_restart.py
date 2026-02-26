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

import json
from storage.fill_journal import FillJournal
from accounting.position_manager import PositionManager


def test_wal_corrupted_line_recovery(tmp_path):
    wal_path = tmp_path / "test_wal.jsonl"

    journal = FillJournal(path=str(wal_path))
    pm = PositionManager(starting_cash=100_000, enable_wal=True)
    pm.journal = journal

    class DummyFill:
        def __init__(self):
            self.symbol = "NG"
            self.qty = 1.0
            self.price = 100.0
            self.side = "BUY"
            self.fill_id = "X1"
            self.event_id = "E1"
            self.commission = 0.0

    # записываем корректный fill
    pm.apply_fill(DummyFill())

    # вручную дописываем битую строку
    with open(wal_path, "a") as f:
        f.write("CORRUPTED_LINE_WITHOUT_JSON\n")

    # восстановление
    pm2 = PositionManager(starting_cash=100_000, enable_wal=True)
    pm2.journal = FillJournal(path=str(wal_path))
    pm2.recover_from_journal()

    # не должно падать, должна примениться только валидная запись
    assert pm2.positions["NG"].qty == 1.0