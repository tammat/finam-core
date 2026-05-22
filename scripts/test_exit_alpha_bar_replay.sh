#!/usr/bin/env bash
set -euo pipefail

export PYTHONPATH="${PYTHONPATH:-src}"

python -m py_compile \
  src/finam_core/research/exit_alpha_policy.py \
  src/scripts/replay_exit_alpha_policy_bar_by_bar.py

grep -q "strategy_exit_alpha_bar_replay" src/scripts/replay_exit_alpha_policy_bar_by_bar.py
grep -q "EXIT_ALPHA_BAR_REPLAY" src/scripts/replay_exit_alpha_policy_bar_by_bar.py
grep -q "replay_single_trade_bar_by_bar" src/finam_core/research/exit_alpha_policy.py

echo "TEST_EXIT_ALPHA_BAR_REPLAY_OK"
