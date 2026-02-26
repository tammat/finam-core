import signal
import sys
from accounting.position_manager import PositionManager
from storage.snapshot_repository import SnapshotRepository

INITIAL_CASH = 100_000.0


def bootstrap():
    snapshot_repo = SnapshotRepository()
    snapshot = snapshot_repo.load()

    pm = PositionManager(
        starting_cash=INITIAL_CASH,
        enable_wal=True,
        recover=False,   # recovery вызываем вручную
    )

    # 1️⃣ Snapshot restore
    if snapshot:
        pm.restore_from_snapshot(snapshot)

    # 2️⃣ WAL replay
    pm.recover_from_journal()

    return pm


def main():
    pm = bootstrap()

    print("=== ENGINE BOOTSTRAPPED ===")
    print("Cash:", pm.cash)
    print("Equity:", pm.total_equity())
    print("Realized PnL:", pm.realized_pnl)



def shutdown(pm):
    print("Shutting down safely...")
    pm.save_snapshot_and_rotate()
    sys.exit(0)

signal.signal(signal.SIGINT, lambda s, f: shutdown(pm))
signal.signal(signal.SIGTERM, lambda s, f: shutdown(pm))
if __name__ == "__main__":
    main()