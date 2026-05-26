#!/usr/bin/env bash
set -euo pipefail

export PYTHONPATH=src

python -m py_compile \
  src/scripts/build_regime_scorecard.py

grep -q "CREATE OR REPLACE VIEW regime_scorecard_v1" \
  sql/create_regime_scorecard_v1.sql

grep -q "regime_direction" \
  sql/create_regime_scorecard_v1.sql

grep -q "edge_reason" \
  sql/create_regime_scorecard_v1.sql

python src/scripts/build_regime_scorecard.py --help \
  | grep -q -- "--continuous-symbol"

echo "REGIME_SCORECARD_V1_COMPILE_OK"
