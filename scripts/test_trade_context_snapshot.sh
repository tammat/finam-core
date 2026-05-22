#!/usr/bin/env bash
set -euo pipefail

export PYTHONPATH="${PYTHONPATH:-src}"

python -m py_compile \
  src/finam_core/analytics/trade_context_snapshot.py \
  src/finam_core/analytics/trade_context_snapshot_repository.py \
  src/scripts/build_trade_context_snapshots.py

grep -q "trade_context_snapshots" src/finam_core/analytics/trade_context_snapshot_repository.py
grep -q "context_quality" src/finam_core/analytics/trade_context_snapshot_repository.py
grep -q "TRADE_CONTEXT_SNAPSHOT_SUMMARY" src/scripts/build_trade_context_snapshots.py

echo "TEST_TRADE_CONTEXT_SNAPSHOT_OK"
