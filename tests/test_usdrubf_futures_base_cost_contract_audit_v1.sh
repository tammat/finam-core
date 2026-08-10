#!/usr/bin/env bash
set -euo pipefail

cd /opt/finam-core || exit 1
export PYTHONPATH=src

SCRIPT=src/scripts/research/build_usdrubf_futures_base_cost_contract_audit_v1.py

echo "=== TEST_USDRUBF_FUTURES_BASE_COST_CONTRACT_AUDIT_V1 ==="

OUTPUT="$(python "$SCRIPT")"

printf '%s\n' "$OUTPUT"

grep -q \
'^SOURCE_FILE .*build_universe_trend_pullback_canonical_adapter_screen_v1.py' \
<<< "$OUTPUT"

grep -q \
'^SOURCE_FILE .*build_trend_pullback_canonical_robustness_v1.py' \
<<< "$OUTPUT"

grep -q \
'^SOURCE_FILE .*build_trend_pullback_canonical_equity_base_cost_validation_v1.py' \
<<< "$OUTPUT"

grep -q \
'^symbol=USDRUBF@RTSX$' \
<<< "$OUTPUT"

grep -q \
'^commission_model=MOEX_MAKER_TAKER_FALLBACK$' \
<<< "$OUTPUT"

grep -q '^entry_liquidity_role=TAKER$' <<< "$OUTPUT"
grep -q '^exit_liquidity_role=TAKER$' <<< "$OUTPUT"

grep -q \
'^canonical_monetary_scale=PRICE_DELTA_X_1000_RUB$' \
<<< "$OUTPUT"

grep -q \
'^baseline_slippage_round_trip_rub=2$' \
<<< "$OUTPUT"

grep -q \
'^stress_slippage_round_trip_rub=20$' \
<<< "$OUTPUT"

grep -q '^funding_used=0$' <<< "$OUTPUT"
grep -q '^funding_separate=1$' <<< "$OUTPUT"

grep -q '^runtime_changed=0$' <<< "$OUTPUT"
grep -q '^execution_changed=0$' <<< "$OUTPUT"
grep -q '^orders_changed=0$' <<< "$OUTPUT"
grep -q '^fills_changed=0$' <<< "$OUTPUT"
grep -q '^economic_edge_claimed=0$' <<< "$OUTPUT"
grep -q '^micro_live_allowed=0$' <<< "$OUTPUT"

grep -q \
'^VERDICT=USDRUBF_FUTURES_BASE_COST_CONTRACT_AUDIT_V1_READY$' \
<<< "$OUTPUT"

echo "VERDICT=TEST_USDRUBF_FUTURES_BASE_COST_CONTRACT_AUDIT_V1_OK"
