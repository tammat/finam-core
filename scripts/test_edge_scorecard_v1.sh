#!/usr/bin/env bash
set -euo pipefail

cd /opt/finam-core

PY_BIN="${PY_BIN:-/opt/finam-core/venv/bin/python}"

if [[ ! -x "$PY_BIN" ]]; then
  PY_BIN="$(command -v python3)"
fi

echo "TEST_EDGE_SCORECARD_V1_START"

"$PY_BIN" -m py_compile \
  src/scripts/observability/build_edge_scorecard_v1.py

"$PY_BIN" src/scripts/observability/build_edge_scorecard_v1.py \
  > /tmp/edge_scorecard_v1.out

grep -q "=== EDGE SCORECARD V1 ===" /tmp/edge_scorecard_v1.out
grep -q "ПОДТВЕРЖДЁННЫЙ EDGE" /tmp/edge_scorecard_v1.out
grep -q "LKOH@MISX" /tmp/edge_scorecard_v1.out
grep -q "EDGE" /tmp/edge_scorecard_v1.out || true

echo "TEST_EDGE_SCORECARD_V1_OK"
