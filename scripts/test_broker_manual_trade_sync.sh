#!/usr/bin/env bash
set -euo pipefail

export PYTHONPATH="${PYTHONPATH:-src}"

python -m py_compile \
  src/finam_core/manual/broker_manual_trade_sync.py \
  src/scripts/sync_manual_trades_from_broker.py

grep -q "REAL_MANUAL_BROKER" src/finam_core/manual/broker_manual_trade_sync.py
grep -q "paper_only" src/finam_core/manual/broker_manual_trade_sync.py

echo "TEST_BROKER_MANUAL_TRADE_SYNC_OK"
