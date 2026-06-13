#!/usr/bin/env bash
set -euo pipefail

cd /opt/finam-core

PY_BIN="${PY_BIN:-/opt/finam-core/venv/bin/python}"
[[ -x "$PY_BIN" ]] || PY_BIN="$(command -v python3)"

echo "TEST_EDGE_SCORECARD_UNIVERSE_PROFIT_CONCENTRATION_V1_START"

"$PY_BIN" -m py_compile src/scripts/analytics/build_edge_scorecard_universe_v1.py

"$PY_BIN" src/scripts/analytics/build_edge_scorecard_universe_v1.py \
  --min-trades 30 \
  > /tmp/edge_scorecard_universe_profit_concentration_v1.out

grep -q "top1_day_share" /tmp/edge_scorecard_universe_profit_concentration_v1.out
grep -q "top3_day_share" /tmp/edge_scorecard_universe_profit_concentration_v1.out
grep -q "profit_concentration" /tmp/edge_scorecard_universe_profit_concentration_v1.out

echo "TEST_EDGE_SCORECARD_UNIVERSE_PROFIT_CONCENTRATION_V1_OK"
