from accounting.position_manager import PositionManager
from storage.fill_journal import FillJournal
from storage.snapshot_repository import SnapshotRepository
from tests.test_position_idempotency import make_fill
def test_snapshot_fencing_consistency(tmp_path):
    wal_path = tmp_path / "wal.jsonl"

    pm = PositionManager(starting_cash=100_000, enable_wal=True)
    pm.journal = FillJournal(path=str(wal_path))

    # 3 fills
    for i in range(3):
        pm.apply_fill(make_fill(f"S{i}"))

    snapshot = pm.get_snapshot()
    snapshot_path = tmp_path / "snapshot.json"
    SnapshotRepository(str(snapshot_path)).save(snapshot)

    # 2 more fills
    for i in range(2):
        pm.apply_fill(make_fill(f"T{i}"))

    # restart
    pm2 = PositionManager(starting_cash=0, enable_wal=True)
    pm2.journal = FillJournal(path=str(wal_path))

    pm2.load_snapshot(snapshot)
    pm2.recover_from_journal()

    assert pm2.total_equity() == pm.total_equity()