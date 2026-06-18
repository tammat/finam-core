#!/usr/bin/env bash
set -euo pipefail

cd "$(git rev-parse --show-toplevel)"

echo "=== RUN TODAY CLOSED PNL STATUS V1 ON 8088 ==="
echo "runtime_allow=0"
echo "execution_enabled=0"
echo "real_trading_enabled=0"
echo "db_update=0"

PYTHONPATH=src python3 src/scripts/runtime/build_today_closed_pnl_status_v1.py \
  --serve \
  --host 0.0.0.0 \
  --port 8088
