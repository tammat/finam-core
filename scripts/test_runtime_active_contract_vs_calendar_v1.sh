#!/usr/bin/env bash
set -euo pipefail

ROOT="$(git rev-parse --show-toplevel)"
cd "$ROOT"
export PYTHONPATH=src

python3 -m py_compile \
  src/scripts/analytics/build_runtime_active_contract_vs_calendar_v1.py

RUNTIME_ACTIVE_CONTRACT_SYMBOLS="BRN6@RTSX,NGN6@RTSX" \
python3 src/scripts/analytics/build_runtime_active_contract_vs_calendar_v1.py \
  | tee /tmp/runtime_active_contract_vs_calendar_v1.log

grep -q "RUNTIME ACTIVE CONTRACT VS CALENDAR V1" /tmp/runtime_active_contract_vs_calendar_v1.log
grep -q "RUNTIME_SYMBOLS" /tmp/runtime_active_contract_vs_calendar_v1.log
grep -q "CONTRACT_ALIGNMENT" /tmp/runtime_active_contract_vs_calendar_v1.log
grep -q "RUNTIME_ACTIVE_CONTRACT_VS_CALENDAR_V1_OK" /tmp/runtime_active_contract_vs_calendar_v1.log

echo "TEST_RUNTIME_ACTIVE_CONTRACT_VS_CALENDAR_V1_OK"
