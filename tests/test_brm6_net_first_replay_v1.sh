#!/usr/bin/env bash
set -euo pipefail

cd /opt/finam-core || exit 1
export PYTHONPATH=src

echo "=== TEST_BRM6_NET_FIRST_REPLAY_V1 ==="

OUTPUT="$(
python \
src/scripts/research/build_brm6_net_first_replay_v1.py
)"

printf '%s\n' "$OUTPUT"

grep -q '^BRM6_NET_FIRST_REPLAY_ROW ' \
<<< "$OUTPUT"

grep -q \
'^transaction_cost_bps=8.0$' \
<<< "$OUTPUT"

grep -q \
'^transaction_cost_semantics=MEDIAN_PRICE_X_BPS_DIV_10000$' \
<<< "$OUTPUT"

grep -q \
'^cost_injected_as=COMMISSION_PER_MONETARY_SCALE$' \
<<< "$OUTPUT"

grep -q \
'^original_regime_cost_contract_reconstructed=1$' \
<<< "$OUTPUT"

grep -q \
'^missing_source_table_required=0$' \
<<< "$OUTPUT"

grep -Eq \
'decision=WOULD_(ADMIT|REJECT)' \
<<< "$OUTPUT"

grep -q '^runtime_changed=0$' <<< "$OUTPUT"
grep -q '^execution_changed=0$' <<< "$OUTPUT"
grep -q '^orders_changed=0$' <<< "$OUTPUT"
grep -q '^fills_changed=0$' <<< "$OUTPUT"
grep -q '^micro_live_allowed=0$' <<< "$OUTPUT"

grep -q \
'^VERDICT=BRM6_NET_FIRST_REPLAY_V1_READY$' \
<<< "$OUTPUT"

echo \
"VERDICT=TEST_BRM6_NET_FIRST_REPLAY_V1_OK"
