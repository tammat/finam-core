#!/usr/bin/env bash
set -euo pipefail

cd /opt/finam-core || exit 1
export PYTHONPATH=src

SCRIPT=src/scripts/research/build_trend_pullback_canonical_futures_base_cost_validation_v1.py

echo "=== TEST_TREND_PULLBACK_CANONICAL_FUTURES_BASE_COST_VALIDATION_V1 ==="

OUTPUT="$(python "$SCRIPT")"

printf '%s\n' "$OUTPUT"

grep -q '^symbol=USDRUBF@RTSX$' <<< "$OUTPUT"

grep -q \
'^canonical_oos_trades=2573$' \
<<< "$OUTPUT"

grep -q \
'^FUTURES_BASE_COST_ROW scenario=REGISTRY_BASELINE .*survive=0$' \
<<< "$OUTPUT"

grep -q \
'^FUTURES_BASE_COST_ROW scenario=ONE_TICK_STRESS .*survive=0$' \
<<< "$OUTPUT"

grep -q \
'^final_status=REJECT_AFTER_BASE_COSTS$' \
<<< "$OUTPUT"

grep -q \
'^commission_model=MOEX_MAKER_TAKER_FALLBACK$' \
<<< "$OUTPUT"

grep -q '^funding_used=0$' <<< "$OUTPUT"
grep -q '^funding_separate=1$' <<< "$OUTPUT"
grep -q '^economic_edge_claimed=0$' <<< "$OUTPUT"
grep -q '^micro_live_allowed=0$' <<< "$OUTPUT"

grep -q \
'^VERDICT=TREND_PULLBACK_CANONICAL_FUTURES_BASE_COST_VALIDATION_V1_READY$' \
<<< "$OUTPUT"

echo "USDRUBF_status=REJECT_AFTER_BASE_COSTS"
echo "economic_edge_claimed=0"
echo "micro_live_allowed=0"

echo "VERDICT=TEST_TREND_PULLBACK_CANONICAL_FUTURES_BASE_COST_VALIDATION_V1_OK"
