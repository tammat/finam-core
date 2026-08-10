#!/usr/bin/env bash
set -euo pipefail

cd /opt/finam-core || exit 1

echo \
"=== TEST UNIVERSE TREND PULLBACK TRUE GROSS SCREEN V1 ==="

python -m py_compile \
  src/scripts/research/build_universe_trend_pullback_true_gross_screen_v1.py

OUTPUT="$(
  PYTHONPATH=src \
  python \
    src/scripts/research/build_universe_trend_pullback_true_gross_screen_v1.py
)"

echo "$OUTPUT"

grep -q \
  'mode=true_gross_signal_screen' \
  <<< "$OUTPUT"

grep -q \
  'strategy_code=TREND_PULLBACK_V1' \
  <<< "$OUTPUT"

grep -q 'symbols=5' <<< "$OUTPUT"
grep -q 'variants=3' <<< "$OUTPUT"

for symbol in \
  'USDRUBF@RTSX' \
  'NVTK@MISX' \
  'PLZL@MISX' \
  'VTBR@MISX' \
  'T@MISX'
do
    grep -q \
      "SYMBOL_ROW symbol=${symbol}" \
      <<< "$OUTPUT"
done

grep -q \
  'signal_metric_source=GROSS_PNL' \
  <<< "$OUTPUT"

grep -q \
  'execution_costs_used=0' \
  <<< "$OUTPUT"

grep -q \
  'parameter_search_performed=0' \
  <<< "$OUTPUT"

grep -q \
  'purged_oos_used=1' \
  <<< "$OUTPUT"

grep -q \
  'economic_edge_claimed=0' \
  <<< "$OUTPUT"

grep -q \
  'db_writes_performed=0' \
  <<< "$OUTPUT"

grep -q 'runtime_changed=0' \
  <<< "$OUTPUT"

grep -q 'execution_changed=0' \
  <<< "$OUTPUT"

grep -q 'orders_changed=0' \
  <<< "$OUTPUT"

grep -q 'fills_changed=0' \
  <<< "$OUTPUT"

grep -q 'micro_live_allowed=0' \
  <<< "$OUTPUT"

grep -Eq \
'VERDICT=UNIVERSE_TREND_PULLBACK_TRUE_GROSS_(CANDIDATES_FOUND|NO_CANDIDATES)' \
<<< "$OUTPUT"

echo
echo "=== TRUE GROSS CONTRACT ==="

if grep -nE \
'metric[[:space:]]*=[[:space:]]*metrics\(' \
src/scripts/research/build_universe_trend_pullback_true_gross_screen_v1.py
then
    echo "ERROR=NET_METRICS_USED_IN_TREND_PULLBACK_SCREEN"
    exit 1
fi

echo \
"VERDICT=TREND_PULLBACK_TRUE_GROSS_METRIC_CONTRACT_OK"

echo
echo "=== DIFF CHECK ==="
git diff --check

echo
echo "=== WORKTREE ==="
git status --short

echo
echo \
"VERDICT=TEST_UNIVERSE_TREND_PULLBACK_TRUE_GROSS_SCREEN_V1_OK"
