#!/usr/bin/env bash
set -euo pipefail

cd /opt/finam-core
export PYTHONPATH=src

PY_BIN="/opt/finam-core/venv/bin/python"
if [ -x "/opt/finam-core/.venv/bin/python" ]; then
  PY_BIN="/opt/finam-core/.venv/bin/python"
fi

echo "=== CRYPTO DAILY BACKFILL JOB V1 ==="
date -Is

"$PY_BIN" src/scripts/research/binance_crypto_backfill_v1.py \
  --symbols BTCUSD,ETHUSD \
  --timeframes M1,M5 \
  --hours 30 \
  --apply

"$PY_BIN" src/scripts/observability/build_crypto_research_dashboard_v1.py

echo "CRYPTO_DAILY_BACKFILL_JOB_V1_OK"
