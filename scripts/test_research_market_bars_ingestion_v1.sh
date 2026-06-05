#!/usr/bin/env bash
set -euo pipefail

export PYTHONPATH=src

python3 -m py_compile \
  src/finam_core/research/market_bars_ingestion.py \
  src/scripts/research/test_research_market_bars_ingestion_v1.py

python3 src/scripts/research/test_research_market_bars_ingestion_v1.py | \
  tee /tmp/research_market_bars_ingestion_v1.log

grep -q "RESEARCH_MARKET_BARS_INGESTION_V1_OK" \
  /tmp/research_market_bars_ingestion_v1.log

psql "$DATABASE_URL" -c "
select
  symbol,
  timeframe,
  ts,
  open,
  high,
  low,
  close,
  volume,
  source
from market_bars
where symbol='TESTBTCUSD'
  and source='research_ingestion_test_v1'
order by ts desc
limit 5;
"

psql "$DATABASE_URL" -c "
delete from market_bars
where symbol='TESTBTCUSD'
  and source='research_ingestion_test_v1';
"

echo TEST_RESEARCH_MARKET_BARS_INGESTION_V1_OK
