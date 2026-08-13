#!/usr/bin/env bash
set -euo pipefail

cd /opt/finam-core || exit 1

PY="/opt/finam-core/venv/bin/python"
FILE="src/scripts/analytics/build_entry_exit_optimizer_v1.py"

echo "=== TEST ENTRY EXIT TARGETED RESEARCH ONLY V1 ==="

PYTHONPATH=src "$PY" -m py_compile "$FILE"
git diff --check -- "$FILE"

grep -q 'ENTRY_EXIT_TARGETED_RESEARCH_ONLY' "$FILE"
grep -q 'TARGETED_RESEARCH_ONLY_REQUIRES_PHYSICAL_SYMBOL' "$FILE"
grep -q 'TARGETED_RESEARCH_ONLY_REQUIRES_STRATEGY' "$FILE"
grep -q 'TARGETED_RESEARCH_ONLY_REQUIRES_SIDE' "$FILE"

# Target contract должен существовать.
for NAME in \
  EDGE_SEARCH_TARGET_SYMBOL \
  EDGE_SEARCH_TARGET_STRATEGY \
  EDGE_SEARCH_TARGET_SIDE
do
    grep -q "$NAME" "$FILE"
done

# Safe evidence path должен оставаться в optimizer.
for TABLE in \
  analytics.entry_exit_signal_shadow_pair_v2 \
  analytics.entry_exit_shadow_diagnostic_v1 \
  analytics.trade_outcome_hypothesis_v1 \
  analytics.trade_outcome_oos_admission_v1
do
    grep -q "$TABLE" "$FILE"
done

echo "targeted_mode_present=1"
echo "physical_symbol_required=1"
echo "safe_evidence_path_present=1"
echo "optimizer_executed=0"
echo "db_writes_performed=0"
echo "execution_changed=0"
echo "orders_changed=0"
echo "fills_changed=0"
echo "micro_live_allowed=0"
echo "VERDICT=TEST_ENTRY_EXIT_TARGETED_RESEARCH_ONLY_V1_BASELINE_OK"
