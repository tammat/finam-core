#!/usr/bin/env bash
set -euo pipefail

cd /opt/finam-core || exit 1

echo "=== TEST BTCUSD SIGNAL EDGE DISCOVERY V1 ==="

python -m py_compile \
  src/scripts/research/build_btcusd_signal_edge_discovery_v1.py

OUTPUT="$(
  PYTHONPATH=src \
  python src/scripts/research/build_btcusd_signal_edge_discovery_v1.py
)"

echo "$OUTPUT"

grep -q 'mode=gross_signal_edge_discovery' <<< "$OUTPUT"
grep -q 'signal_symbol=BTCUSD' <<< "$OUTPUT"

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
grep -q 'purged_oos_used=1' <<< "$OUTPUT"

grep -q 'db_writes_performed=0' <<< "$OUTPUT"
grep -q 'runtime_changed=0' <<< "$OUTPUT"
grep -q 'execution_changed=0' <<< "$OUTPUT"
grep -q 'orders_changed=0' <<< "$OUTPUT"
grep -q 'fills_changed=0' <<< "$OUTPUT"
grep -q 'micro_live_allowed=0' <<< "$OUTPUT"

if grep -qE 'IMOEX2|MXU6' \
  src/scripts/research/build_btcusd_signal_edge_discovery_v1.py
then
    echo "ERROR=FOREIGN_SYMBOL_REFERENCE_FOUND"
    exit 1
fi

grep -Eq \
'VERDICT=BTCUSD_GROSS_SIGNAL_(CANDIDATES_FOUND|NO_CANDIDATES)' \
<<< "$OUTPUT"

echo
echo "=== DIFF CHECK ==="
git diff --check

echo
echo "=== WORKTREE ==="
git status --short

echo
echo "VERDICT=TEST_BTCUSD_SIGNAL_EDGE_DISCOVERY_V1_OK"
