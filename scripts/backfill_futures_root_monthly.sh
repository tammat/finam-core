#!/usr/bin/env bash
set -euo pipefail

ROOT="${1:?root required, example: BR}"
TIMEFRAME="${2:-M5}"
FROM_DATE="${3:?from-date required}"
TO_DATE="${4:?to-date required}"
MAX_CONTRACTS="${MAX_CONTRACTS:-12}"
SLEEP_SEC="${SLEEP_SEC:-1}"

echo "ROOT_MONTHLY_BACKFILL_START root=$ROOT timeframe=$TIMEFRAME from=$FROM_DATE to=$TO_DATE max_contracts=$MAX_CONTRACTS"

cur="$FROM_DATE"

while [[ "$cur" < "$TO_DATE" ]]; do
  next=$(date -I -d "$cur +1 month")
  if [[ "$next" > "$TO_DATE" ]]; then
    next="$TO_DATE"
  fi

  echo "ROOT_MONTHLY_BACKFILL_CHUNK root=$ROOT timeframe=$TIMEFRAME from=$cur to=$next"

  PYTHONPATH=src /opt/finam-core/venv/bin/python \
    src/scripts/ingestion/backfill_finam_futures_market_bars.py \
    --roots "$ROOT" \
    --timeframe "$TIMEFRAME" \
    --max-contracts "$MAX_CONTRACTS" \
    --start-date "$cur" \
    --end-date "$next" || true

  psql "$DATABASE_URL" -c "
  select
    symbol,
    timeframe,
    count(*) as bars,
    min(ts) as first_ts,
    max(ts) as last_ts
  from market_bars
  where symbol like '${ROOT}%@RTSX'
    and timeframe='${TIMEFRAME}'
  group by symbol, timeframe
  order by symbol;
  " || true

  cur="$next"
  sleep "$SLEEP_SEC"
done

echo "ROOT_MONTHLY_BACKFILL_DONE root=$ROOT timeframe=$TIMEFRAME"
