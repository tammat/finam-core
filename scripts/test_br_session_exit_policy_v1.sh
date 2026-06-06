#!/usr/bin/env bash
set -euo pipefail

export PYTHONPATH=src

python3 -m py_compile \
  src/finam_core/exits/br_session_exit_policy.py \
  src/scripts/research/replay_br_session_exit_policy_v1.py

python3 src/scripts/research/replay_br_session_exit_policy_v1.py | \
  tee /tmp/br_session_exit_policy_v1.log

grep -q "REPLAY BR SESSION EXIT POLICY V1.1" /tmp/br_session_exit_policy_v1.log
grep -q "runtime_changed=0" /tmp/br_session_exit_policy_v1.log
grep -q "BASELINE_HISTORICAL_TIME_EXIT" /tmp/br_session_exit_policy_v1.log
grep -q "BR_SESSION_EXIT_V1" /tmp/br_session_exit_policy_v1.log
grep -Eq "VERDICT=VALIDATED|VERDICT=NOT_VALIDATED|VERDICT=NO_DATA" /tmp/br_session_exit_policy_v1.log

echo BR_SESSION_EXIT_POLICY_V1_1_OK
