#!/usr/bin/env bash
set -euo pipefail

cd /opt/finam-core

PY_BIN="${PY_BIN:-/opt/finam-core/venv/bin/python}"
if [[ ! -x "$PY_BIN" ]]; then
  PY_BIN="$(command -v python3)"
fi

echo "TEST_NG_POSITION_RECONCILE_FIX_V1_START"

"$PY_BIN" -m py_compile src/scripts/observability/build_ng_position_reconcile_fix_v1.py

SYMBOL=NGN6@RTSX "$PY_BIN" src/scripts/observability/build_ng_position_reconcile_fix_v1.py --dry-run \
  > /tmp/ng_position_reconcile_fix_v1.out

grep -q "NG POSITION RECONCILE FIX V1" /tmp/ng_position_reconcile_fix_v1.out
grep -q "mode=DRY_RUN" /tmp/ng_position_reconcile_fix_v1.out
grep -q "fills_net_qty" /tmp/ng_position_reconcile_fix_v1.out
grep -q "verdict=" /tmp/ng_position_reconcile_fix_v1.out

echo "TEST_NG_POSITION_RECONCILE_FIX_V1_OK"
