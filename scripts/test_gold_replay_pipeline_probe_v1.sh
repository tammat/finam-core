#!/usr/bin/env bash
set -euo pipefail

ROOT="$(git rev-parse --show-toplevel)"
cd "$ROOT"
export PYTHONPATH=src

python3 -m py_compile \
  src/scripts/analytics/build_gold_replay_pipeline_probe_v1.py

GOLD_REPLAY_SYMBOL="GDM6@RTSX" \
GOLD_REPLAY_TIMEFRAME="M5" \
python3 src/scripts/analytics/build_gold_replay_pipeline_probe_v1.py \
  | tee /tmp/gold_replay_pipeline_probe_v1.log

grep -q "GOLD REPLAY PIPELINE PROBE V1" /tmp/gold_replay_pipeline_probe_v1.log
grep -q "PROBE_ROW symbol=GDM6@RTSX" /tmp/gold_replay_pipeline_probe_v1.log
grep -q "GOLD_REPLAY_PIPELINE_PROBE_V1_OK" /tmp/gold_replay_pipeline_probe_v1.log

echo "TEST_GOLD_REPLAY_PIPELINE_PROBE_V1_OK"
