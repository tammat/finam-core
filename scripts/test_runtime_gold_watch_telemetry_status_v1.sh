#!/usr/bin/env bash
set -euo pipefail

cd "$(git rev-parse --show-toplevel)"

echo "=== TEST RUNTIME GOLD WATCH TELEMETRY STATUS V1 ==="
echo "runtime_allow=0"
echo "execution_enabled=0"
echo "real_trading_enabled=0"

python3 -m py_compile \
  src/scripts/runtime/build_runtime_gold_watch_telemetry_v1.py

grep -q "GOLD_WATCH_TELEMETRY_READY_FOR_RUNTIME_REVIEW_STATUS_V1" \
  src/scripts/runtime/build_runtime_gold_watch_telemetry_v1.py

grep -q "READY_FOR_RUNTIME_REVIEW" \
  src/scripts/runtime/build_runtime_gold_watch_telemetry_v1.py

PYTHONPATH=src /opt/finam-core/venv/bin/python src/scripts/runtime/build_runtime_gold_watch_telemetry_v1.py \
  | tee /tmp/runtime_gold_watch_telemetry_status_v1.log

grep -q "RUNTIME GOLD WATCH TELEMETRY" /tmp/runtime_gold_watch_telemetry_status_v1.log
grep -q "symbol=GDU6@RTSX" /tmp/runtime_gold_watch_telemetry_status_v1.log
grep -q "runtime_allow=0" /tmp/runtime_gold_watch_telemetry_status_v1.log
grep -q "execution_enabled=0" /tmp/runtime_gold_watch_telemetry_status_v1.log

if grep -q "TELEMETRY_ERROR reason=invalid_status status=READY_FOR_RUNTIME_REVIEW" /tmp/runtime_gold_watch_telemetry_status_v1.log; then
  echo "FAIL: READY_FOR_RUNTIME_REVIEW still treated as invalid"
  exit 1
fi

echo TEST_RUNTIME_GOLD_WATCH_TELEMETRY_STATUS_V1_OK
