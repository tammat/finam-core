#!/usr/bin/env bash
set -euo pipefail

cd /opt/finam-core

PY_BIN="${PY_BIN:-/opt/finam-core/venv/bin/python}"

if [[ ! -x "$PY_BIN" ]]; then
  PY_BIN="$(command -v python3)"
fi

echo "TEST_LIVE_ORDERBOOK_PROBE_V1_START"

"$PY_BIN" -m py_compile \
  src/scripts/research/live_orderbook_probe_v1.py

grep -q "SubscribeOrderBook" src/scripts/research/live_orderbook_probe_v1.py
grep -q "OrderBookRequest" src/scripts/research/live_orderbook_probe_v1.py
grep -q "verdict=" src/scripts/research/live_orderbook_probe_v1.py

echo "TEST_LIVE_ORDERBOOK_PROBE_V1_OK"
