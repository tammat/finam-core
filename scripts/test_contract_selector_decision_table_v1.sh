#!/usr/bin/env bash
set -euo pipefail

ROOT="$(git rev-parse --show-toplevel)"
cd "$ROOT"
export PYTHONPATH=src

python3 -m py_compile \
  src/scripts/analytics/build_contract_selector_decision_table_v1.py

timeout 60s python3 src/scripts/analytics/build_contract_selector_decision_table_v1.py \
  | tee /tmp/contract_selector_decision_table_v1.log

grep -q "CONTRACT SELECTOR DECISION TABLE V1" /tmp/contract_selector_decision_table_v1.log
grep -q "DECISION_ROWS" /tmp/contract_selector_decision_table_v1.log
grep -q "DECISION_ROW root=BR" /tmp/contract_selector_decision_table_v1.log
grep -q "DECISION_ROW root=NG" /tmp/contract_selector_decision_table_v1.log
grep -q "CONTRACT_SELECTOR_DECISION_TABLE_V1_OK" /tmp/contract_selector_decision_table_v1.log

echo "TEST_CONTRACT_SELECTOR_DECISION_TABLE_V1_OK"
