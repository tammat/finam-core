#!/usr/bin/env bash
set -euo pipefail

export PYTHONPATH="${PYTHONPATH:-src}"

python -m py_compile \
  src/finam_core/strategy/futures/ng_conservative_breakout_m1.py \
  src/scripts/replay_ng_conservative_breakout_m1.py

grep -q "NG_CONSERVATIVE_BREAKOUT_M1" src/scripts/replay_ng_conservative_breakout_m1.py
grep -q "NgConservativeBreakoutM1" src/scripts/replay_ng_conservative_breakout_m1.py

echo "TEST_NG_CONSERVATIVE_BREAKOUT_M1_OK"
