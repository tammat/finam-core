#!/usr/bin/env bash
set -euo pipefail

export PYTHONPATH="${PYTHONPATH:-src}"

python -m py_compile \
  src/finam_core/research/ng_contract_universe.py \
  src/scripts/replay/replay_ng_universe.py

grep -q "NGM6@RTSX" \
  src/finam_core/research/ng_contract_universe.py

grep -q "replay_exit_alpha_grid.py" \
  src/scripts/replay/replay_ng_universe.py

grep -q "NG_UNIVERSE_REPLAY_SUMMARY" \
  src/scripts/replay/replay_ng_universe.py

echo "TEST_NG_REPLAY_UNIVERSE_OK"
