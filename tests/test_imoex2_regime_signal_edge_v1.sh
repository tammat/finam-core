#!/usr/bin/env bash
set -euo pipefail

cd /opt/finam-core || exit 1

echo "=== TEST IMOEX2 REGIME SIGNAL EDGE V1 ==="

python -m py_compile \
  src/scripts/research/build_imoex2_regime_signal_edge_v1.py

OUTPUT="$(
  PYTHONPATH=src \
  python src/scripts/research/build_imoex2_regime_signal_edge_v1.py
)"

echo "$OUTPUT"

grep -q \
  'mode=gross_regime_signal_edge_discovery' \
  <<< "$OUTPUT"

grep -q 'signal_symbol=IMOEX2' <<< "$OUTPUT"

grep -q \
  'regime_coverage_ratio=0.99' \
  <<< "$OUTPUT"

grep -q 'REGIME_DISCOVERY_ROW' <<< "$OUTPUT"
grep -q 'regime=compression' <<< "$OUTPUT"
grep -q 'regime=range_normal' <<< "$OUTPUT"
grep -q 'regime=trend_up' <<< "$OUTPUT"
grep -q 'regime=trend_down' <<< "$OUTPUT"

grep -q \
  'gross_regime_signal_edge_search=1' \
  <<< "$OUTPUT"

grep -q 'economic_edge_claimed=0' <<< "$OUTPUT"
grep -q 'multiple_testing_adjusted=1' <<< "$OUTPUT"
grep -q 'execution_instrument_used=0' <<< "$OUTPUT"
grep -q 'execution_costs_used=0' <<< "$OUTPUT"
grep -q 'purged_oos_used=1' <<< "$OUTPUT"

grep -q 'db_writes_performed=0' <<< "$OUTPUT"
grep -q 'runtime_changed=0' <<< "$OUTPUT"
grep -q 'execution_changed=0' <<< "$OUTPUT"
grep -q 'orders_changed=0' <<< "$OUTPUT"
grep -q 'fills_changed=0' <<< "$OUTPUT"
grep -q 'micro_live_allowed=0' <<< "$OUTPUT"

grep -Eq \
'VERDICT=IMOEX2_REGIME_SIGNAL_(CANDIDATES_FOUND|NO_CANDIDATES)' \
<<< "$OUTPUT"

echo
echo "=== DIFF CHECK ==="
git diff --check

echo
echo "=== WORKTREE ==="
git status --short

echo
echo \
"VERDICT=TEST_IMOEX2_REGIME_SIGNAL_EDGE_V1_OK"
