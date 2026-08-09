#!/usr/bin/env bash
set -euo pipefail

cd /opt/finam-core || exit 1

echo \
"=== TEST UNIVERSE INDEPENDENT FAMILY RUNNABILITY AUDIT V1 ==="

python -m py_compile \
  src/scripts/research/build_universe_independent_family_runnability_audit_v1.py

OUTPUT="$(
  PYTHONPATH=src \
  python \
    src/scripts/research/build_universe_independent_family_runnability_audit_v1.py
)"

echo "$OUTPUT"

grep -q \
  'mode=read_only_runnability_audit' \
  <<< "$OUTPUT"

for family in \
  TREND_PULLBACK \
  RELATIVE_STRENGTH \
  INTERMARKET_LEAD_LAG \
  REGIME \
  SESSION \
  VOLATILITY_STATE
do
    grep -q \
      "RUNNABILITY_ROW family=${family}" \
      <<< "$OUTPUT"
done

grep -q 'SUMMARY_ROW' <<< "$OUTPUT"

grep -q \
  'runnable_signal_family_names=' \
  <<< "$OUTPUT"

grep -q \
  'conditioning_layer_names=' \
  <<< "$OUTPUT"

grep -q \
  'blocked_signal_family_names=' \
  <<< "$OUTPUT"

echo
echo "=== CONDITIONING LAYER CONTRACT ==="

for family in \
  REGIME \
  SESSION \
  VOLATILITY_STATE
do
    grep -q \
      "RUNNABILITY_ROW family=${family} .*classification=CONDITIONING_LAYER .*runnable_signal_family=0 .*status=CONDITIONING_LAYER" \
      <<< "$OUTPUT"
done

echo \
"VERDICT=INDEPENDENT_FAMILY_CONDITIONING_CONTRACT_OK"

grep -q 'family_execution_performed=0' \
  <<< "$OUTPUT"
grep -q 'backtest_performed=0' \
  <<< "$OUTPUT"
grep -q 'parameter_search_performed=0' \
  <<< "$OUTPUT"
grep -q 'economic_edge_claimed=0' \
  <<< "$OUTPUT"
grep -q 'db_writes_performed=0' \
  <<< "$OUTPUT"
grep -q 'runtime_changed=0' <<< "$OUTPUT"
grep -q 'execution_changed=0' <<< "$OUTPUT"
grep -q 'orders_changed=0' <<< "$OUTPUT"
grep -q 'fills_changed=0' <<< "$OUTPUT"
grep -q 'micro_live_allowed=0' <<< "$OUTPUT"

grep -q \
'VERDICT=UNIVERSE_INDEPENDENT_FAMILY_RUNNABILITY_AUDIT_V1_READY' \
<<< "$OUTPUT"

echo
echo "=== DIFF CHECK ==="
git diff --check

echo
echo "=== WORKTREE ==="
git status --short

echo
echo \
"VERDICT=TEST_UNIVERSE_INDEPENDENT_FAMILY_RUNNABILITY_AUDIT_V1_OK"
