#!/usr/bin/env bash
set -euo pipefail

cd /opt/finam-core || exit 1

echo "=== TEST IMOEX2 GROSS SIGNAL EDGE DISCOVERY V1 ==="

python -m py_compile \
  src/scripts/research/build_imoex2_multi_family_discovery_v1.py

OUTPUT="$(
  PYTHONPATH=src \
  python src/scripts/research/build_imoex2_multi_family_discovery_v1.py
)"

echo "$OUTPUT"

grep -q \
  'mode=gross_signal_edge_discovery' \
  <<< "$OUTPUT"

grep -q 'signal_symbol=IMOEX2' <<< "$OUTPUT"

grep -q \
  'families=MOMENTUM,MEAN_REVERSION,BREAKOUT' \
  <<< "$OUTPUT"

grep -q 'execution_instrument_used=0' <<< "$OUTPUT"
grep -q 'execution_costs_used=0' <<< "$OUTPUT"
grep -q 'commission=0' <<< "$OUTPUT"
grep -q 'slippage=0' <<< "$OUTPUT"

grep -q 'family=MOMENTUM' <<< "$OUTPUT"
grep -q 'family=MEAN_REVERSION' <<< "$OUTPUT"
grep -q 'family=BREAKOUT' <<< "$OUTPUT"

grep -q 'gross_signal_edge_search=1' <<< "$OUTPUT"
grep -q 'economic_edge_claimed=0' <<< "$OUTPUT"

grep -q \
  'execution_replay_required_for_promotion=1' \
  <<< "$OUTPUT"

grep -q 'purged_oos_used=1' <<< "$OUTPUT"

grep -q 'db_writes_performed=0' <<< "$OUTPUT"
grep -q 'runtime_changed=0' <<< "$OUTPUT"
grep -q 'execution_changed=0' <<< "$OUTPUT"
grep -q 'orders_changed=0' <<< "$OUTPUT"
grep -q 'fills_changed=0' <<< "$OUTPUT"
grep -q 'micro_live_allowed=0' <<< "$OUTPUT"

# Signal-discovery не должен содержать MXU6 economics.
if grep -q 'execution_cost_proxy=' <<< "$OUTPUT"; then
    echo "ERROR=EXECUTION_COST_PROXY_LEAKED"
    exit 1
fi

if grep -q 'round_trip_cost_rub=' <<< "$OUTPUT"; then
    echo "ERROR=EXECUTION_COSTS_LEAKED"
    exit 1
fi

grep -Eq \
'VERDICT=IMOEX2_GROSS_SIGNAL_(CANDIDATES_FOUND|NO_CANDIDATES)' \
<<< "$OUTPUT"

echo
echo "=== DIFF CHECK ==="
git diff --check

echo
echo "=== WORKTREE ==="
git status --short

echo
echo \
"VERDICT=TEST_IMOEX2_GROSS_SIGNAL_EDGE_DISCOVERY_V1_OK"
