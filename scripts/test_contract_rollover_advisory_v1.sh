#!/usr/bin/env bash
set -euo pipefail

ROOT="$(git rev-parse --show-toplevel)"
cd "$ROOT"
export PYTHONPATH=src

python3 -m py_compile \
  src/scripts/analytics/build_contract_rollover_advisory_v1.py

RUNTIME_ACTIVE_CONTRACT_SYMBOLS="BRN6@RTSX,NGN6@RTSX" \
python3 src/scripts/analytics/build_contract_rollover_advisory_v1.py \
  | tee /tmp/contract_rollover_advisory_v1.log

grep -q "CONTRACT ROLLOVER ADVISORY V1" /tmp/contract_rollover_advisory_v1.log
grep -q "ROLLOVER_ADVISORY_ROWS" /tmp/contract_rollover_advisory_v1.log
grep -q "ADVISORY_ROW" /tmp/contract_rollover_advisory_v1.log
grep -q "CONTRACT_ROLLOVER_ADVISORY_V1_OK" /tmp/contract_rollover_advisory_v1.log

echo "TEST_CONTRACT_ROLLOVER_ADVISORY_V1_OK"
