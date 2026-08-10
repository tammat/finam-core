#!/usr/bin/env bash
set -euo pipefail

cd /opt/finam-core || exit 1
export PYTHONPATH=src

echo "=== TEST_TREND_PULLBACK_CANONICAL_EQUITY_BASE_COST_VALIDATION_V1 ==="

OUTPUT="$(
python -u \
  src/scripts/research/build_trend_pullback_canonical_equity_base_cost_validation_v1.py
)"

printf '%s\n' "$OUTPUT"

ROWS="$(
grep -c '^EQUITY_BASE_COST_ROW ' \
<<< "$OUTPUT"
)"

if [ "$ROWS" -ne 2 ]; then
    echo "ERROR=EXPECTED_2_EQUITY_COST_ROWS actual=$ROWS"
    exit 1
fi

grep -q \
'^EQUITY_BASE_COST_ROW symbol=NVTK@MISX ' \
<<< "$OUTPUT"

grep -q \
'^EQUITY_BASE_COST_ROW symbol=PLZL@MISX ' \
<<< "$OUTPUT"

grep -q '^base_costs_used=1$' <<< "$OUTPUT"
grep -q '^execution_spread_impact_used=0$' <<< "$OUTPUT"
grep -q '^economic_edge_claimed=0$' <<< "$OUTPUT"
grep -q '^micro_live_allowed=0$' <<< "$OUTPUT"

grep -q \
'^VERDICT=TREND_PULLBACK_CANONICAL_EQUITY_BASE_COST_VALIDATION_V1_READY$' \
<<< "$OUTPUT"

echo "rows_checked=2"
echo "runtime_changed=0"
echo "execution_changed=0"
echo "orders_changed=0"
echo "fills_changed=0"
echo "micro_live_allowed=0"
echo "VERDICT=TEST_TREND_PULLBACK_CANONICAL_EQUITY_BASE_COST_VALIDATION_V1_OK"
