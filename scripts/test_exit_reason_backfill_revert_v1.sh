#!/usr/bin/env bash
set -euo pipefail

cd /opt/finam-core
export PYTHONPATH=src

python3 -m py_compile src/scripts/analytics/revert_exit_reason_backfill_v1.py

python3 src/scripts/analytics/revert_exit_reason_backfill_v1.py | \
  tee /tmp/exit_reason_backfill_revert_v1.log

grep -q "EXIT REASON BACKFILL REVERT V1" /tmp/exit_reason_backfill_revert_v1.log
grep -q "REVERT_CANDIDATES=" /tmp/exit_reason_backfill_revert_v1.log
grep -q "VERDICT=DRY_RUN_ONLY" /tmp/exit_reason_backfill_revert_v1.log
grep -q "EXIT_REASON_BACKFILL_REVERT_V1_OK" /tmp/exit_reason_backfill_revert_v1.log

echo TEST_EXIT_REASON_BACKFILL_REVERT_V1_OK
