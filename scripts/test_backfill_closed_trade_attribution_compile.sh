#!/usr/bin/env bash
set -euo pipefail

export PYTHONPATH=src

python -m py_compile src/scripts/backfill_closed_trade_attribution.py
./scripts/test_backfill_closed_trade_attribution_sql.sh

echo "OK: backfill closed trade attribution tests"
