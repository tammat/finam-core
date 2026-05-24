#!/usr/bin/env bash
set -euo pipefail

export PYTHONPATH="${PYTHONPATH:-src}"

python -m py_compile \
  src/finam_core/strategy/futures/ng_conservative_breakout.py \
  src/scripts/replay/replay_ng_conservative_breakout.py

grep -q "NG_CONSERVATIVE_BREAKOUT" src/scripts/replay/replay_ng_conservative_breakout.py
grep -q "NG_REPLAY_SUMMARY" src/scripts/replay/replay_ng_conservative_breakout.py

echo "TEST_REPLAY_NG_CONSERVATIVE_BREAKOUT_OK"
