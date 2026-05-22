#!/usr/bin/env bash
set -euo pipefail

export PYTHONPATH="${PYTHONPATH:-src}"

python -m py_compile \
  src/scripts/build_best_exit_alpha_policy.py \
  src/scripts/sync_best_exit_alpha_to_radar.py

grep -q "strategy_best_exit_alpha_policy" src/scripts/build_best_exit_alpha_policy.py
grep -q "RADAR_EXIT_ALPHA_CANDIDATE" src/scripts/build_best_exit_alpha_policy.py
grep -q "strategy_exit_alpha_radar" src/scripts/sync_best_exit_alpha_to_radar.py

echo "TEST_BEST_EXIT_ALPHA_POLICY_OK"
