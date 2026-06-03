#!/usr/bin/env bash
set -euo pipefail

cd /opt/finam-core

PY_BIN="${PY_BIN:-/opt/finam-core/venv/bin/python}"
if [[ ! -x "$PY_BIN" ]]; then
  PY_BIN="$(command -v python3)"
fi

echo "TEST_NG_POSITION_RECONCILE_FIX_PROJECTION_JSON_QTY_V1_START"

"$PY_BIN" -m py_compile src/scripts/observability/build_ng_position_reconcile_fix_v1.py

grep -q "state->>'qty'" src/scripts/observability/build_ng_position_reconcile_fix_v1.py
grep -q "position_projection хранит количество внутри JSONB state" src/scripts/observability/build_ng_position_reconcile_fix_v1.py

SYMBOL=NGN6@RTSX "$PY_BIN" src/scripts/observability/build_ng_position_reconcile_fix_v1.py --dry-run \
  > /tmp/ng_position_reconcile_fix_projection_json_qty_v1.out

grep -q "NG POSITION RECONCILE FIX V1" /tmp/ng_position_reconcile_fix_projection_json_qty_v1.out
grep -q "position_projection_qty=4.0" /tmp/ng_position_reconcile_fix_projection_json_qty_v1.out
grep -q "verdict=NOOP" /tmp/ng_position_reconcile_fix_projection_json_qty_v1.out

echo "TEST_NG_POSITION_RECONCILE_FIX_PROJECTION_JSON_QTY_V1_OK"
