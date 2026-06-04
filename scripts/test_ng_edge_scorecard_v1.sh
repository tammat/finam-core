#!/usr/bin/env bash
set -euo pipefail

cd /opt/finam-core

PY_BIN="${PY_BIN:-/opt/finam-core/venv/bin/python}"
[[ -x "$PY_BIN" ]] || PY_BIN="$(command -v python3)"

echo "TEST_NG_EDGE_SCORECARD_V1_START"

"$PY_BIN" -m py_compile src/scripts/analytics/build_ng_edge_scorecard_v1.py

SYMBOL=NGN6@RTSX "$PY_BIN" src/scripts/analytics/build_ng_edge_scorecard_v1.py \
  > /tmp/ng_edge_scorecard.out

grep -q "NG EDGE SCORECARD V1" /tmp/ng_edge_scorecard.out
grep -q "EDGE STATUS" /tmp/ng_edge_scorecard.out
grep -q "FINAL VERDICT" /tmp/ng_edge_scorecard.out
grep -q "RESEARCH_ONLY" /tmp/ng_edge_scorecard.out

echo "TEST_NG_EDGE_SCORECARD_V1_OK"
