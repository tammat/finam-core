#!/usr/bin/env bash
set -euo pipefail

cd /opt/finam-core || exit 1
export PYTHONPATH=src

SCRIPT=src/scripts/research/build_trend_pullback_economic_gate_regression_v1.py

echo "=== TEST_TREND_PULLBACK_ECONOMIC_GATE_REGRESSION_V1 ==="

OUTPUT="$(python "$SCRIPT")"

printf '%s\n' "$OUTPUT"

grep -q \
'^ECONOMIC_GATE_REGRESSION_ROW symbol=NVTK@MISX .*status=REJECT_NEGATIVE_EXPECTANCY$' \
<<< "$OUTPUT"

grep -q \
'^ECONOMIC_GATE_REGRESSION_ROW symbol=PLZL@MISX .*status=REJECT_NEGATIVE_EXPECTANCY$' \
<<< "$OUTPUT"

grep -q \
'^ECONOMIC_GATE_REGRESSION_ROW symbol=USDRUBF@RTSX .*status=REJECT_NEGATIVE_EXPECTANCY$' \
<<< "$OUTPUT"

grep -q '^regression_cases=3$' <<< "$OUTPUT"
grep -q '^rejected_cases=3$' <<< "$OUTPUT"

grep -q \
'^canonical_trade_replay_used=0$' \
<<< "$OUTPUT"

grep -q \
'^regression_mode=AGGREGATE_DECISION_SEMANTICS$' \
<<< "$OUTPUT"

grep -q '^db_writes_performed=0$' <<< "$OUTPUT"
grep -q '^runtime_changed=0$' <<< "$OUTPUT"
grep -q '^execution_changed=0$' <<< "$OUTPUT"
grep -q '^orders_changed=0$' <<< "$OUTPUT"
grep -q '^fills_changed=0$' <<< "$OUTPUT"
grep -q '^economic_edge_claimed=0$' <<< "$OUTPUT"
grep -q '^micro_live_allowed=0$' <<< "$OUTPUT"

grep -q \
'^VERDICT=TREND_PULLBACK_ECONOMIC_GATE_REGRESSION_V1_OK$' \
<<< "$OUTPUT"

echo "VERDICT=TEST_TREND_PULLBACK_ECONOMIC_GATE_REGRESSION_V1_OK"
