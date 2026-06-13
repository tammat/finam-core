#!/usr/bin/env bash
set -euo pipefail

cd /opt/finam-core

PY_BIN="${PY_BIN:-/opt/finam-core/venv/bin/python}"
[[ -x "$PY_BIN" ]] || PY_BIN="$(command -v python3)"

echo "TEST_EDGE_SCORECARD_UNIVERSE_V1_START"

"$PY_BIN" -m py_compile src/scripts/analytics/build_edge_scorecard_universe_v1.py

"$PY_BIN" src/scripts/analytics/build_edge_scorecard_universe_v1.py \
  --min-trades 1 \
  > /tmp/edge_scorecard_universe_v1.out

grep -q "EDGE SCORECARD UNIVERSE V1" /tmp/edge_scorecard_universe_v1.out
grep -q "RANKING" /tmp/edge_scorecard_universe_v1.out
grep -q "FINAL_SUMMARY" /tmp/edge_scorecard_universe_v1.out

echo "TEST_EDGE_SCORECARD_UNIVERSE_V1_OK"
