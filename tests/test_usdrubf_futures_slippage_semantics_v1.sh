#!/usr/bin/env bash
set -euo pipefail

cd /opt/finam-core || exit 1
export PYTHONPATH=src

SCRIPT=src/scripts/research/build_usdrubf_futures_slippage_semantics_v1.py

echo "=== TEST_USDRUBF_FUTURES_SLIPPAGE_SEMANTICS_V1 ==="

OUTPUT="$(python "$SCRIPT")"

printf '%s\n' "$OUTPUT"

grep -q \
'^SLIPPAGE_PROFILE_ROW symbol=USDRUBF@RTSX .*slippage_per_side_rub=1' \
<<< "$OUTPUT"

grep -q \
'round_trip_slippage_rub=2' \
<<< "$OUTPUT"

grep -q \
'^SLIPPAGE_SCALE_ROW .*tick_value_rub=10 .*registry_slippage_ticks_per_side=0.1' \
<<< "$OUTPUT"

grep -q \
'^BASELINE_SCENARIO code=REGISTRY_BASELINE ' \
<<< "$OUTPUT"

grep -q \
'^STRESS_SCENARIO code=ONE_TICK_STRESS .*slippage_per_side_rub=10 .*round_trip_slippage_rub=20' \
<<< "$OUTPUT"

grep -q \
'^slippage_application_semantics=FIXED_MONETARY_PER_SIDE$' \
<<< "$OUTPUT"

grep -q '^slippage_currency=RUB$' <<< "$OUTPUT"
grep -q '^actual_slippage_evidence=0$' <<< "$OUTPUT"
grep -q '^registry_source_is_actual_execution_evidence=0$' <<< "$OUTPUT"
grep -q '^registry_source_is_normalized_fallback=1$' <<< "$OUTPUT"

grep -q '^runtime_changed=0$' <<< "$OUTPUT"
grep -q '^execution_changed=0$' <<< "$OUTPUT"
grep -q '^orders_changed=0$' <<< "$OUTPUT"
grep -q '^fills_changed=0$' <<< "$OUTPUT"
grep -q '^economic_edge_claimed=0$' <<< "$OUTPUT"
grep -q '^micro_live_allowed=0$' <<< "$OUTPUT"

grep -q \
'^VERDICT=USDRUBF_FUTURES_SLIPPAGE_SEMANTICS_V1_READY$' \
<<< "$OUTPUT"

echo "slippage_unit_semantics=RUB"
echo "slippage_application_semantics=PER_SIDE_FIXED"
echo "registry_baseline_round_trip_rub=2"
echo "one_tick_stress_round_trip_rub=20"
echo "actual_slippage_evidence=0"
echo "economic_edge_claimed=0"
echo "micro_live_allowed=0"

echo "VERDICT=TEST_USDRUBF_FUTURES_SLIPPAGE_SEMANTICS_V1_OK"
