#!/usr/bin/env bash
set -euo pipefail

export PYTHONPATH=src

python - <<'INNER_PY'
from pathlib import Path

cmp_text = Path("src/finam_core/recovery/position_rebuild_comparator.py").read_text(encoding="utf-8")
gate_text = Path("src/finam_core/reconciliation/startup_recovery_gate.py").read_text(encoding="utf-8")

checks = {
    "cmp_has_snapshot_aware": "SnapshotAwarePortfolioRebuilder" in cmp_text,
    "gate_has_snapshot_aware": "SnapshotAwarePortfolioRebuilder" in gate_text,
    "gate_no_old_constructor": "portfolio_rebuilder=PortfolioRebuilder(reader=EventStoreReader())" not in gate_text,
    "gate_no_old_import": "from finam_core.recovery.portfolio_rebuilder import PortfolioRebuilder" not in gate_text,
    "cmp_has_rebuild_aggregate_support": "rebuild_aggregate" in cmp_text,
    "cmp_has_snapshot_rebuild_call": "self.portfolio_rebuilder.rebuild(" in cmp_text,
}

failed = [name for name, ok in checks.items() if not ok]
if failed:
    print("SNAPSHOT_AWARE_COMPARATOR_INTEGRATION_FAILED", failed)
    raise SystemExit(1)

print("SNAPSHOT_AWARE_COMPARATOR_INTEGRATION_OK")
INNER_PY
