#!/usr/bin/env bash
set -euo pipefail

ROOT="$(git rev-parse --show-toplevel)"
cd "$ROOT"

export PYTHONPATH=src

python3 -m py_compile \
  src/scripts/analytics/build_instrument_radar_scorecard_v1.py

python3 \
  src/scripts/analytics/build_instrument_radar_scorecard_v1.py \
  | tee /tmp/instrument_radar_scorecard_v1.log

grep -q "INSTRUMENT RADAR SCORECARD V1" \
  /tmp/instrument_radar_scorecard_v1.log

grep -q "RADAR_ROWS" \
  /tmp/instrument_radar_scorecard_v1.log

grep -q "SUMMARY_ROW" \
  /tmp/instrument_radar_scorecard_v1.log

grep -q "INSTRUMENT_RADAR_SCORECARD_V1_OK" \
  /tmp/instrument_radar_scorecard_v1.log

echo TEST_INSTRUMENT_RADAR_SCORECARD_V1_OK
