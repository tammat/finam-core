from accounting.position_manager import PositionManager
from domain.risk.risk_stack import RiskStack
from storage.snapshot_repository import SnapshotRepository

def test_freeze_survives_snapshot(tmp_path):
    snap = tmp_path / "snap.json"

    pm = PositionManager(100_000)
    pm.snapshot_repo = SnapshotRepository(str(snap))

    pm.risk_stack.frozen = True
    pm.risk_stack.freeze_reason = "drawdown"

    pm.save_snapshot_and_rotate()

    pm2 = PositionManager(100_000)
    pm2.snapshot_repo = SnapshotRepository(str(snap))

    data = pm2.snapshot_repo.load()
    pm2.load_snapshot(data)

    assert pm2.risk_stack.frozen is True
    assert pm2.risk_stack.freeze_reason == "drawdown"