#!/usr/bin/env bash
set -euo pipefail

export PYTHONPATH=src

python3 -m py_compile \
  src/scripts/research/binance_crypto_backfill_v1.py \
  src/finam_core/research/market_data_provider.py \
  src/finam_core/research/market_bars_ingestion.py

# Удаляем старый тестовый мусор ingestion-теста, если он остался.
psql "$DATABASE_URL" -c "
delete from market_bars
where symbol='TESTBTCUSD'
  and source='research_ingestion_test_v1';
"

python3 src/scripts/research/binance_crypto_backfill_v1.py \
  --symbols BTCUSD,ETHUSD \
  --timeframes M1,M5 \
  --hours 24 | tee /tmp/binance_crypto_backfill_v1_dry.log

grep -q "VERDICT=DRY_RUN" /tmp/binance_crypto_backfill_v1_dry.log
grep -q "BACKFILL_ROW symbol=BTCUSD timeframe=M1" /tmp/binance_crypto_backfill_v1_dry.log
grep -q "BACKFILL_ROW symbol=ETHUSD timeframe=M5" /tmp/binance_crypto_backfill_v1_dry.log

python3 src/scripts/research/binance_crypto_backfill_v1.py \
  --symbols BTCUSD,ETHUSD \
  --timeframes M1,M5 \
  --hours 24 \
  --apply | tee /tmp/binance_crypto_backfill_v1_apply.log

grep -q "VERDICT=APPLIED" /tmp/binance_crypto_backfill_v1_apply.log
grep -q "TOTAL_BARS_WRITTEN=" /tmp/binance_crypto_backfill_v1_apply.log

psql "$DATABASE_URL" -c "
select
  symbol,
  timeframe,
  count(*) as bars,
  min(ts) as first_ts,
  max(ts) as last_ts,
  min(source) as source
from market_bars
where symbol in ('BTCUSD','ETHUSD')
  and source='binance_public_klines'
group by symbol, timeframe
order by symbol, timeframe;
"

echo BINANCE_CRYPTO_BACKFILL_V1_OK
