#!/usr/bin/env bash
set -euo pipefail

export PYTHONPATH=src

python -m py_compile src/scripts/replay_br_pipeline.py

grep -q "FROM market_bars" src/scripts/replay_br_pipeline.py
grep -q "source = 'finam_grpc_bars_v1'" src/scripts/replay_br_pipeline.py

if grep -q "FROM market_data" src/scripts/replay_br_pipeline.py; then
  echo "ERROR: replay still reads market_data"
  exit 1
fi

echo "REPLAY_BR_PIPELINE_MARKET_BARS_SOURCE_OK"
