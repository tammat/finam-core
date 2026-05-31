#!/usr/bin/env bash
set -euo pipefail

cd /opt/finam-core
export PYTHONPATH=src

echo "TEST_BROKER_POSITION_SYNC_ACTIVE_BR_LOG_V1_START"

python -m py_compile src/finam_core/pipelines/paper_pipeline.py

if grep -n "PIPE_BROKER_POSITION_SYNC_OK" -A5 -B5 src/finam_core/pipelines/paper_pipeline.py | grep -q "BRM6@RTSX"; then
  echo "TEST_BROKER_POSITION_SYNC_ACTIVE_BR_LOG_V1_FAILED hardcoded_BRM6_still_present"
  exit 1
fi

grep -q "self.br_breakout_symbol" src/finam_core/pipelines/paper_pipeline.py

echo "TEST_BROKER_POSITION_SYNC_ACTIVE_BR_LOG_V1_OK"
