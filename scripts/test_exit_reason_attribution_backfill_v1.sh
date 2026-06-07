#!/usr/bin/env bash
set -euo pipefail

cd /opt/finam-core
export PYTHONPATH=src

test -f src/scripts/analytics/build_exit_reason_attribution_backfill_v1.py

python3 -m py_compile src/scripts/analytics/build_exit_reason_attribution_backfill_v1.py

python3 src/scripts/analytics/build_exit_reason_attribution_backfill_v1.py | \
  tee /tmp/exit_reason_attribution_backfill_v1.log

grep -q "EXIT REASON ATTRIBUTION BACKFILL V1" /tmp/exit_reason_attribution_backfill_v1.log
grep -q "MATCH_CANDIDATES" /tmp/exit_reason_attribution_backfill_v1.log
grep -q "TOTAL_CANDIDATES=" /tmp/exit_reason_attribution_backfill_v1.log
grep -q "VERDICT=DRY_RUN_ONLY" /tmp/exit_reason_attribution_backfill_v1.log
grep -q "EXIT_REASON_ATTRIBUTION_BACKFILL_V1_OK" /tmp/exit_reason_attribution_backfill_v1.log

echo TEST_EXIT_REASON_ATTRIBUTION_BACKFILL_V1_OK
