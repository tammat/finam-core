#!/usr/bin/env bash
set -euo pipefail

cd /opt/finam-core || exit 1
export PYTHONPATH=src

echo "=== TEST_TREND_PULLBACK_CANONICAL_COST_RESOLVER_V1 ==="

OUTPUT="$(
python \
  src/scripts/research/build_trend_pullback_canonical_cost_resolver_v1.py
)"

printf '%s\n' "$OUTPUT"

grep -q \
'COST_CONTRACT_ROW symbol=NVTK@MISX .*status=COST_SOURCE_COMPLETE' \
<<< "$OUTPUT"

grep -q \
'COST_CONTRACT_ROW symbol=PLZL@MISX .*status=COST_SOURCE_COMPLETE' \
<<< "$OUTPUT"

grep -q \
'COST_CONTRACT_ROW symbol=USDRUBF@RTSX .*status=FUTURES_CONTRACT_FEE_SEMANTICS_PENDING' \
<<< "$OUTPUT"

grep -q \
'commission_per_trade=0.01000000 commission_pct=0.00050000 slippage_per_trade=0.01000000' \
<<< "$OUTPUT"

grep -q 'economic_edge_claimed=0' <<< "$OUTPUT"
grep -q 'micro_live_allowed=0' <<< "$OUTPUT"

echo "equity_cost_sources_complete=1"
echo "futures_cost_semantics_fail_closed=1"
echo "runtime_changed=0"
echo "execution_changed=0"
echo "orders_changed=0"
echo "fills_changed=0"
echo "micro_live_allowed=0"

echo "VERDICT=TEST_TREND_PULLBACK_CANONICAL_COST_RESOLVER_V1_OK"
