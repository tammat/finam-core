#!/usr/bin/env bash
set -euo pipefail

cd /opt/finam-core

PY_BIN="${PY_BIN:-/opt/finam-core/venv/bin/python}"
if [[ ! -x "$PY_BIN" ]]; then
  PY_BIN="$(command -v python3)"
fi

echo "TEST_REBUILD_POSITION_PROJECTION_FROM_FILLS_V1_START"

"$PY_BIN" -m py_compile src/scripts/observability/rebuild_position_projection_from_fills_v1.py

"$PY_BIN" src/scripts/observability/rebuild_position_projection_from_fills_v1.py \
  --symbol NGN6@RTSX \
  --dry-run > /tmp/rebuild_position_projection_from_fills_v1.out

grep -q "REBUILD POSITION PROJECTION FROM FILLS V1" /tmp/rebuild_position_projection_from_fills_v1.out
grep -q "verdict=" /tmp/rebuild_position_projection_from_fills_v1.out

echo "TEST_REBUILD_POSITION_PROJECTION_FROM_FILLS_V1_OK"
