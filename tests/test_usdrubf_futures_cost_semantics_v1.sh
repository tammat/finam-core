#!/usr/bin/env bash
set -euo pipefail

cd /opt/finam-core || exit 1
export PYTHONPATH=src

SCRIPT=src/scripts/research/build_usdrubf_futures_cost_semantics_v1.py

echo "=== TEST_USDRUBF_FUTURES_COST_SEMANTICS_V1 ==="

OUTPUT="$(
python "$SCRIPT"
)"

printf '%s\n' "$OUTPUT"

grep -q \
'^MONETARY_SCALE_ROW symbol=USDRUBF@RTSX .*lot_underlying_units=1000 .*tick_size=0.01 .*calculated_tick_value_rub=10' \
<<< "$OUTPUT"

grep -q \
'^MOEX_FEE_RATE_ROW maker_rate_pct=0.0 unaddressed_taker_rate_pct=0.00462 addressed_rate_pct=0.00154$' \
<<< "$OUTPUT"

grep -q \
'^FALLBACK_COST_CONTRACT actual_finam_fee_available=0 ordinary_fee_model=MOEX_MAKER_TAKER base_entry_role=TAKER base_exit_role=TAKER exercise_fee_included=0 funding_separate=1$' \
<<< "$OUTPUT"

grep -q \
'^canonical_monetary_scale=PRICE_DELTA_X_1000_RUB$' \
<<< "$OUTPUT"

grep -q \
'^legacy_fixed_fee_fields_authoritative=0$' \
<<< "$OUTPUT"

grep -q '^db_writes_performed=0$' <<< "$OUTPUT"
grep -q '^runtime_changed=0$' <<< "$OUTPUT"
grep -q '^execution_changed=0$' <<< "$OUTPUT"
grep -q '^orders_changed=0$' <<< "$OUTPUT"
grep -q '^fills_changed=0$' <<< "$OUTPUT"
grep -q '^economic_edge_claimed=0$' <<< "$OUTPUT"
grep -q '^micro_live_allowed=0$' <<< "$OUTPUT"

grep -q \
'^VERDICT=USDRUBF_FUTURES_COST_SEMANTICS_V1_READY$' \
<<< "$OUTPUT"

echo "actual_finam_fee_available=0"
echo "fallback_fee_model=MOEX_MAKER_TAKER"
echo "monetary_scale_validated=1"
echo "legacy_fee_semantics_resolved=1"
echo "economic_edge_claimed=0"
echo "micro_live_allowed=0"

echo "VERDICT=TEST_USDRUBF_FUTURES_COST_SEMANTICS_V1_OK"
