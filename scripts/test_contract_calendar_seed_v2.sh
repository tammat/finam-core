#!/usr/bin/env bash
set -euo pipefail

ROOT="$(git rev-parse --show-toplevel)"
cd "$ROOT"
export PYTHONPATH=src

python3 -m py_compile src/scripts/analytics/seed_contract_calendar_v2.py

CONTRACT_CALENDAR_ROOTS="BR,NG" \
CONTRACT_CALENDAR_HORIZON_DAYS=370 \
python3 src/scripts/analytics/seed_contract_calendar_v2.py \
  | tee /tmp/contract_calendar_seed_v2.log

grep -q "CONTRACT CALENDAR SEED V2" /tmp/contract_calendar_seed_v2.log
grep -q "SEED_ROW" /tmp/contract_calendar_seed_v2.log
grep -q "CONTRACT_CALENDAR_SEED_V2_OK" /tmp/contract_calendar_seed_v2.log

python3 src/scripts/analytics/build_rollover_status_report_v1.py \
  | tee /tmp/rollover_status_after_seed_v2.log

grep -q "ROLLOVER_ROW" /tmp/rollover_status_after_seed_v2.log
grep -q "ROLLOVER_STATUS_REPORT_V1_OK" /tmp/rollover_status_after_seed_v2.log

echo "TEST_CONTRACT_CALENDAR_SEED_V2_OK"
