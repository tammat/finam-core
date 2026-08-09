#!/usr/bin/env bash
set -euo pipefail

cd /opt/finam-core || exit 1

echo "=== TEST UNIVERSE SIGNAL EXECUTION COST CONTRACT AUDIT V1 ==="

python -m py_compile \
  src/scripts/research/build_universe_signal_execution_cost_contract_audit_v1.py

OUTPUT="$(
  PYTHONPATH=src \
  python \
    src/scripts/research/build_universe_signal_execution_cost_contract_audit_v1.py
)"

echo "$OUTPUT"

grep -q 'PNL_CONTRACT_ROW' <<< "$OUTPUT"
grep -q 'COST_CONTRACT_ROW' <<< "$OUTPUT"
grep -q 'TIMESTAMP_CONTRACT_ROW' <<< "$OUTPUT"
grep -q 'METRICS_ROW' <<< "$OUTPUT"
grep -q 'hidden_execution_costs_detected=' <<< "$OUTPUT"

grep -q 'db_writes_performed=0' <<< "$OUTPUT"
grep -q 'runtime_changed=0' <<< "$OUTPUT"
grep -q 'execution_changed=0' <<< "$OUTPUT"
grep -q 'orders_changed=0' <<< "$OUTPUT"
grep -q 'fills_changed=0' <<< "$OUTPUT"
grep -q 'micro_live_allowed=0' <<< "$OUTPUT"

grep -Eq \
'VERDICT=UNIVERSE_SIGNAL_SCREEN_(EXECUTION_COST_CONTAMINATION_DETECTED|GROSS_CONTRACT_CONFIRMED)' \
<<< "$OUTPUT"

echo
echo "=== DIFF CHECK ==="
git diff --check

echo
echo "=== WORKTREE ==="
git status --short

echo \
"VERDICT=TEST_UNIVERSE_SIGNAL_EXECUTION_COST_CONTRACT_AUDIT_V1_OK"
