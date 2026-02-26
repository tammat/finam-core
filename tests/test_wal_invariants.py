import copy
from accounting.position_manager import PositionManager
from storage.fill_journal import FillJournal


def test_wal_deterministic_replay(tmp_path):
    wal = tmp_path / "wal.jsonl"

    pm = PositionManager(100_000, enable_wal=True)
    pm.journal = FillJournal(str(wal))

    for i in range(10):
        pm.apply_fill(make_fill(f"S{i}"))

    snapshot_live = copy.deepcopy(pm.get_snapshot())

    pm2 = PositionManager(100_000, enable_wal=True)
    pm2.journal = FillJournal(str(wal))
    pm2.recover_from_journal()

    assert pm2.get_snapshot() == snapshot_live


def test_wal_recovery_idempotent(tmp_path):
    wal = tmp_path / "wal.jsonl"

    pm = PositionManager(100_000, enable_wal=True)
    pm.journal = FillJournal(str(wal))

    for i in range(5):
        pm.apply_fill(make_fill(f"S{i}"))

    pm2 = PositionManager(100_000, enable_wal=True)
    pm2.journal = FillJournal(str(wal))

    pm2.recover_from_journal()
    snap1 = pm2.get_snapshot()

    pm2.recover_from_journal()
    snap2 = pm2.get_snapshot()

    assert snap1 == snap2


class DummyFill:
    def __init__(self, fill_id: str):
        self.symbol = "NG"
        self.qty = 1.0
        self.price = 100.0
        self.side = "BUY"
        self.fill_id = fill_id
        self.event_id = fill_id
        self.commission = 0.0

def make_fill(fill_id: str):
    return DummyFill(fill_id)