#!/usr/bin/env bash
set -euo pipefail

export PYTHONPATH=src

python3 -m py_compile \
  src/finam_core/research/market_data_provider.py \
  src/scripts/research/binance_crypto_backfill_v1.py

python3 src/scripts/research/binance_crypto_backfill_v1.py \
  --symbols BTCUSD,ETHUSD \
  --timeframes M1,M5 \
  --hours 24 | tee /tmp/binance_crypto_backfill_pagination_v1_dry.log

grep -q "VERDICT=DRY_RUN" /tmp/binance_crypto_backfill_pagination_v1_dry.log
grep -q "BACKFILL_ROW symbol=BTCUSD timeframe=M1" /tmp/binance_crypto_backfill_pagination_v1_dry.log
grep -q "BACKFILL_ROW symbol=ETHUSD timeframe=M1" /tmp/binance_crypto_backfill_pagination_v1_dry.log

python3 - <<'PY'
from pathlib import Path
import re

text = Path("/tmp/binance_crypto_backfill_pagination_v1_dry.log").read_text()

m = re.search(r"BACKFILL_ROW symbol=BTCUSD timeframe=M1 bars=(\d+)", text)
if not m:
    raise SystemExit("BTCUSD_M1_ROW_NOT_FOUND")

btc_m1 = int(m.group(1))
if btc_m1 < 1200:
    raise SystemExit(f"BTCUSD_M1_PAGINATION_TOO_FEW_BARS={btc_m1}")

m = re.search(r"BACKFILL_ROW symbol=ETHUSD timeframe=M1 bars=(\d+)", text)
if not m:
    raise SystemExit("ETHUSD_M1_ROW_NOT_FOUND")

eth_m1 = int(m.group(1))
if eth_m1 < 1200:
    raise SystemExit(f"ETHUSD_M1_PAGINATION_TOO_FEW_BARS={eth_m1}")

print(f"PAGINATION_BAR_COUNT_OK btc_m1={btc_m1} eth_m1={eth_m1}")
PY

python3 src/scripts/research/binance_crypto_backfill_v1.py \
  --symbols BTCUSD,ETHUSD \
  --timeframes M1,M5 \
  --hours 24 \
  --apply | tee /tmp/binance_crypto_backfill_pagination_v1_apply.log

grep -q "VERDICT=APPLIED" /tmp/binance_crypto_backfill_pagination_v1_apply.log

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

echo BINANCE_CRYPTO_BACKFILL_PAGINATION_V1_OK
