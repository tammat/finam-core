#!/usr/bin/env bash
set -euo pipefail

export PYTHONPATH="${PYTHONPATH:-src}"

python -m py_compile src/scripts/research/historical_signal_replay_v1.py

grep -q "historical_signal_replay_runs" src/scripts/research/historical_signal_replay_v1.py
grep -q "historical_signal_replay" src/scripts/research/historical_signal_replay_v1.py
grep -q "HISTORICAL_BREAKOUT_V1" src/scripts/research/historical_signal_replay_v1.py
grep -q "build_intraday_pnl.py" src/scripts/research/historical_signal_replay_v1.py
grep -q "build_regime_aware_edge_v1.py" src/scripts/research/historical_signal_replay_v1.py

echo "HISTORICAL_SIGNAL_REPLAY_V1_TEST_OK"
