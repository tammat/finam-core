#!/usr/bin/env bash
set -euo pipefail

ROOT="$(git rev-parse --show-toplevel)"
cd "$ROOT"
export PYTHONPATH=src

python3 -m py_compile \
  src/scripts/analytics/build_active_contract_scorecard_v1.py

python3 src/scripts/analytics/build_active_contract_scorecard_v1.py \
  | tee /tmp/active_contract_scorecard_v1.log

grep -q "ACTIVE CONTRACT SCORECARD V1" /tmp/active_contract_scorecard_v1.log
grep -q "ACTIVE_CONTRACT_ROWS" /tmp/active_contract_scorecard_v1.log
grep -q "ACTIVE_CONTRACT_SCORECARD_V1_OK" /tmp/active_contract_scorecard_v1.log

echo "TEST_ACTIVE_CONTRACT_SCORECARD_V1_OK"
