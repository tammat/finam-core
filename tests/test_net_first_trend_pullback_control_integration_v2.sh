#!/usr/bin/env bash
set -euo pipefail

cd /opt/finam-core || exit 1
export PYTHONPATH=src

SCRIPT="src/scripts/research/build_net_first_trend_pullback_control_integration_v2.py"

echo "=== TEST NET FIRST TREND PULLBACK CONTROL INTEGRATION V2 ==="

python -m py_compile "$SCRIPT"

OUTPUT="$(python "$SCRIPT")"

printf '%s\n' "$OUTPUT"

test "$(
    grep -c \
      '^NET_FIRST_CONTROL_V2_ROW .*robustness_called=0$' \
      <<< "$OUTPUT"
)" -eq 3

grep -q '^candidates=3$' <<< "$OUTPUT"
grep -q '^economic_gate_reject=3$' <<< "$OUTPUT"
grep -q '^economic_gate_pass=0$' <<< "$OUTPUT"
grep -q '^robustness_scheduled=0$' <<< "$OUTPUT"
grep -q '^robustness_saved=3$' <<< "$OUTPUT"

grep -q '^policy_from_config=1$' <<< "$OUTPUT"
grep -q '^negative_controls_from_frozen_v2=1$' <<< "$OUTPUT"
grep -q '^economic_gate_before_robustness=1$' <<< "$OUTPUT"

grep -q '^core_net_first_changed=0$' <<< "$OUTPUT"
grep -q '^shadow_admission_preserved=1$' <<< "$OUTPUT"
grep -q '^enforced_admission_enabled=0$' <<< "$OUTPUT"

grep -q '^runtime_changed=0$' <<< "$OUTPUT"
grep -q '^execution_changed=0$' <<< "$OUTPUT"
grep -q '^orders_changed=0$' <<< "$OUTPUT"
grep -q '^fills_changed=0$' <<< "$OUTPUT"
grep -q '^micro_live_allowed=0$' <<< "$OUTPUT"

grep -q \
  '^VERDICT=NET_FIRST_TREND_PULLBACK_CONTROL_INTEGRATION_V2_OK$' \
  <<< "$OUTPUT"

echo "VERDICT=TEST_NET_FIRST_TREND_PULLBACK_CONTROL_INTEGRATION_V2_OK"
