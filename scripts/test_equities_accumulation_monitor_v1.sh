#!/usr/bin/env bash
set -euo pipefail

echo "=== TEST_EQUITIES_ACCUMULATION_MONITOR_V1 ==="

python3 -m py_compile src/scripts/research/build_equities_accumulation_monitor_v1.py

python3 src/scripts/research/build_equities_accumulation_monitor_v1.py \
  | tee /tmp/equities_accumulation_monitor_v1.log

grep -q "EQUITY_MONITOR_SUMMARY" /tmp/equities_accumulation_monitor_v1.log
grep -q "decision=" /tmp/equities_accumulation_monitor_v1.log
grep -q "VERDICT=EQUITIES_ACCUMULATION_MONITOR_READY" /tmp/equities_accumulation_monitor_v1.log

echo "VERDICT=EQUITIES_ACCUMULATION_MONITOR_TEST_OK"
echo "TEST_EQUITIES_ACCUMULATION_MONITOR_V1_OK"
