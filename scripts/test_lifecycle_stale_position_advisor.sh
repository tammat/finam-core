#!/usr/bin/env bash
set -euo pipefail

export PYTHONPATH="${PYTHONPATH:-src}"

python - <<'PY'
from finam_core.portfolio.lifecycle_stale_position_advisor import (
    LifecycleStalePositionInput,
    build_lifecycle_stale_position_advice,
)

missing = build_lifecycle_stale_position_advice(
    LifecycleStalePositionInput(
        symbol="LKOH@MISX",
        display_name="ЛУКОЙЛ",
        broker_qty=15,
        lifecycle_qty=0,
        managed_qty=15,
        reconciliation_status="BROKER_LIFECYCLE_MISMATCH",
    )
)
assert missing.action == "REBUILD_LIFECYCLE_STATE"
assert missing.block_new_entries is True

stale = build_lifecycle_stale_position_advice(
    LifecycleStalePositionInput(
        symbol="SBER@MISX",
        display_name="Сбербанк",
        broker_qty=0,
        lifecycle_qty=1,
        managed_qty=0,
        reconciliation_status="MISMATCH",
    )
)
assert stale.action == "IGNORE_OR_CLEAN_STALE_LIFECYCLE"
assert stale.block_new_entries is False

print("TEST_LIFECYCLE_STALE_POSITION_ADVISOR_OK")
PY

python -m py_compile \
  src/finam_core/portfolio/lifecycle_stale_position_advisor.py \
  src/scripts/build_lifecycle_stale_position_advice.py
