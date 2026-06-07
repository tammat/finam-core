#!/usr/bin/env bash
set -euo pipefail

cd /opt/finam-core
export PYTHONPATH=src

python3 -m py_compile src/scripts/analytics/build_exit_reason_backfill_historical_v1.py

python3 src/scripts/analytics/build_exit_reason_backfill_historical_v1.py | \
  tee /tmp/exit_reason_backfill_historical_v1.log

grep -q "EXIT REASON BACKFILL HISTORICAL V1" /tmp/exit_reason_backfill_historical_v1.log
grep -q "MATCH_CANDIDATES" /tmp/exit_reason_backfill_historical_v1.log
grep -q "TOTAL_CANDIDATES=" /tmp/exit_reason_backfill_historical_v1.log
grep -q "VERDICT=DRY_RUN_ONLY" /tmp/exit_reason_backfill_historical_v1.log
grep -q "EXIT_REASON_BACKFILL_HISTORICAL_V1_OK" /tmp/exit_reason_backfill_historical_v1.log

echo TEST_EXIT_REASON_BACKFILL_HISTORICAL_V1_OK
