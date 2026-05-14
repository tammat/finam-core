#!/usr/bin/env bash
set -euo pipefail

export PYTHONPATH=src

python -m py_compile \
  src/finam_core/reconciliation/manual_trade_reconciliation.py \
  src/finam_core/reconciliation/manual_position_snapshot_repository.py \
  src/scripts/run_manual_trade_reconciliation.py

echo "OK: manual trade reconciliation runner compiles"
