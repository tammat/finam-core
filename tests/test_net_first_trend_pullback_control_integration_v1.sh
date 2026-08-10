#!/usr/bin/env bash
set -euo pipefail

cd /opt/finam-core || exit 1
export PYTHONPATH=src

SCRIPT=src/scripts/research/build_net_first_trend_pullback_control_integration_v1.py

echo "=== TEST_NET_FIRST_TREND_PULLBACK_CONTROL_INTEGRATION_V1 ==="

OUTPUT="$(python "$SCRIPT")"

printf '%s\n' "$OUTPUT"

grep -q \
'^NET_FIRST_CONTROL_ROW symbol=NVTK@MISX .*robustness_called=0$' \
<<< "$OUTPUT"

grep -q \
'^NET_FIRST_CONTROL_ROW symbol=PLZL@MISX .*robustness_called=0$' \
<<< "$OUTPUT"

grep -q \
'^NET_FIRST_CONTROL_ROW symbol=USDRUBF@RTSX .*robustness_called=0$' \
<<< "$OUTPUT"

grep -q '^candidates=3$' <<< "$OUTPUT"
grep -q '^economic_gate_reject=3$' <<< "$OUTPUT"
grep -q '^economic_gate_pass=0$' <<< "$OUTPUT"
grep -q '^robustness_scheduled=0$' <<< "$OUTPUT"
grep -q '^robustness_saved=3$' <<< "$OUTPUT"

grep -q \
'^economic_gate_before_robustness=1$' \
<<< "$OUTPUT"

grep -q '^runtime_changed=0$' <<< "$OUTPUT"
grep -q '^execution_changed=0$' <<< "$OUTPUT"
grep -q '^orders_changed=0$' <<< "$OUTPUT"
grep -q '^fills_changed=0$' <<< "$OUTPUT"
grep -q '^economic_edge_claimed=0$' <<< "$OUTPUT"
grep -q '^micro_live_allowed=0$' <<< "$OUTPUT"

grep -q \
'^VERDICT=NET_FIRST_TREND_PULLBACK_CONTROL_INTEGRATION_V1_OK$' \
<<< "$OUTPUT"

echo \
"VERDICT=TEST_NET_FIRST_TREND_PULLBACK_CONTROL_INTEGRATION_V1_OK"
