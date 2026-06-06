#!/usr/bin/env bash
set -euo pipefail

export PYTHONPATH=src

python3 -m py_compile \
  src/scripts/analytics/build_br_short_flat_signal_shadow_replay_v1.py

python3 src/scripts/analytics/build_br_short_flat_signal_shadow_replay_v1.py | \
  tee /tmp/br_short_flat_signal_shadow_replay_v1.log

grep -q "BR SHORT FLAT SIGNAL SHADOW REPLAY V1" /tmp/br_short_flat_signal_shadow_replay_v1.log
grep -q "POLICY_SUMMARY" /tmp/br_short_flat_signal_shadow_replay_v1.log
grep -q "BY_STRATEGY_POLICY_2H" /tmp/br_short_flat_signal_shadow_replay_v1.log
grep -q "DECISION_METRICS" /tmp/br_short_flat_signal_shadow_replay_v1.log
grep -Eq "VERDICT=BR_SHORT_FLAT_SIGNAL_EDGE_FOUND|VERDICT=BR_SHORT_FLAT_SIGNAL_EDGE_NOT_VALIDATED|VERDICT=NO_SHORT_REPLAY_DATA" \
  /tmp/br_short_flat_signal_shadow_replay_v1.log

echo BR_SHORT_FLAT_SIGNAL_SHADOW_REPLAY_V1_OK
