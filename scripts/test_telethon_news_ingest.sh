#!/usr/bin/env bash
set -euo pipefail

cd /opt/finam-core
source .venv/bin/activate
export PYTHONPATH=src

python -m py_compile src/finam_core/ai/telethon_news_ingest.py

if grep -R "PlaceOrder\|place_order\|TradeAPI\|OrdersService\|place_market_order\|place_limit_order" -n src/finam_core/ai/telethon_news_ingest.py; then
  echo "ERROR: Telethon ingest contains trading API references"
  exit 1
fi

echo "OK: telethon_news_ingest compile and safety test passed"
