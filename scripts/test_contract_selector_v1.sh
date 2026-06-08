#!/usr/bin/env bash
set -euo pipefail

ROOT="$(git rev-parse --show-toplevel)"
cd "$ROOT"
export PYTHONPATH=src

python3 -m py_compile src/scripts/analytics/build_contract_selector_v1.py

python3 src/scripts/analytics/build_contract_selector_v1.py \
  | tee /tmp/contract_selector_v1.log

grep -q "CONTRACT SELECTOR V1" /tmp/contract_selector_v1.log
grep -q "CONTRACT_SELECTOR_ROWS" /tmp/contract_selector_v1.log
grep -q "SELECTOR_ROW root=BR" /tmp/contract_selector_v1.log
grep -q "SELECTOR_ROW root=NG" /tmp/contract_selector_v1.log
grep -q "CONTRACT_SELECTOR_V1_OK" /tmp/contract_selector_v1.log

echo "TEST_CONTRACT_SELECTOR_V1_OK"
