#!/usr/bin/env bash
set -euo pipefail

export PYTHONPATH="${PYTHONPATH:-src}"

python -m py_compile src/scripts/build_market_radar_candidates.py

grep -q "market_radar_candidates" src/scripts/build_market_radar_candidates.py
grep -q "edge_score" src/scripts/build_market_radar_candidates.py
grep -q "MARKET_RADAR_CANDIDATES_SUMMARY" src/scripts/build_market_radar_candidates.py

echo "TEST_MARKET_RADAR_CANDIDATES_OK"
