#!/usr/bin/env bash
set -euo pipefail

cd /opt/finam-core

PY_BIN="${PY_BIN:-/opt/finam-core/venv/bin/python}"
[[ -x "$PY_BIN" ]] || PY_BIN="$(command -v python3)"

echo "TEST_MATERIALIZE_CLOSED_TRADES_FROM_FILLS_V1_START"

"$PY_BIN" -m py_compile src/scripts/analytics/materialize_closed_trades_from_fills_v1.py

SYMBOL=NGN6@RTSX "$PY_BIN" src/scripts/analytics/materialize_closed_trades_from_fills_v1.py \
  --symbol NGN6@RTSX --dry-run \
  > /tmp/materialize_closed_trades_from_fills_v1.out

grep -q "MATERIALIZE CLOSED TRADES FROM FILLS V1" /tmp/materialize_closed_trades_from_fills_v1.out
grep -q "SYMBOL_SUMMARY symbol=NGN6@RTSX" /tmp/materialize_closed_trades_from_fills_v1.out
grep -q "VERDICT=DRY_RUN_ONLY" /tmp/materialize_closed_trades_from_fills_v1.out

echo "TEST_MATERIALIZE_CLOSED_TRADES_FROM_FILLS_V1_OK"
