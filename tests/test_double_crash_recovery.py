import os
from accounting.position_manager import PositionManager
from storage.fill_journal import FillJournal
from storage.snapshot_repository import SnapshotRepository


def test_double_crash_recovery(tmp_path):
    wal_path = tmp_path / "wal.jsonl"
    snapshot_path = tmp_path / "snapshot.json"

    # ---- Phase 1: initial run ----
    pm = PositionManager(starting_cash=100_000, enable_wal=True)
    pm.journal = FillJournal(path=str(wal_path))
    pm.snapshot_repo = SnapshotRepository(str(snapshot_path))

    class DummyFill:
        def __init__(self, symbol):
            self.symbol = symbol
            self.qty = 1.0
            self.price = 100.0
            self.side = "BUY"
            self.fill_id = symbol
            self.event_id = symbol
            self.commission = 0.0

    # Apply 5 fills
    for i in range(5):
        pm.apply_fill(DummyFill(f"S{i}"))

    # Force snapshot
    pm.save_snapshot_and_rotate()

    # ---- Simulated crash ----
    pm2 = PositionManager(starting_cash=0, enable_wal=True)
    pm2.journal = FillJournal(path=str(wal_path))
    pm2.snapshot_repo = SnapshotRepository(str(snapshot_path))

    snapshot = pm2.snapshot_repo.load()
    pm2.load_snapshot(snapshot)
    pm2.recover_from_journal()

    assert pm2.positions["S0"].qty == 1.0
    assert pm2.positions["S4"].qty == 1.0

    # ---- Second crash ----
    pm3 = PositionManager(starting_cash=0, enable_wal=True)
    pm3.journal = FillJournal(path=str(wal_path))
    pm3.snapshot_repo = SnapshotRepository(str(snapshot_path))

    snapshot = pm3.snapshot_repo.load()
    pm3.load_snapshot(snapshot)
    pm3.recover_from_journal()

    assert pm3.positions["S0"].qty == 1.0
    assert pm3.positions["S4"].qty == 1.0