#!/usr/bin/env bash
set -euo pipefail

SYMBOL="${1:?symbol required}"
TIMEFRAME="${2:-M5}"
FROM_DATE="${3:?from-date required}"
TO_DATE="${4:?to-date required}"

# Для BRN6: контракт июльский 2026, поэтому год назад грузить нельзя.
# Берем практическое окно обращения: не раньше 2026-04-01.
CONTRACT_START="${CONTRACT_START:-2026-04-01}"
CONTRACT_END="${CONTRACT_END:-2026-07-01}"

START="$FROM_DATE"
END="$TO_DATE"

if [[ "$START" < "$CONTRACT_START" ]]; then
  START="$CONTRACT_START"
fi

if [[ "$END" > "$CONTRACT_END" ]]; then
  END="$CONTRACT_END"
fi

echo "MONTHLY_BACKFILL_START symbol=$SYMBOL timeframe=$TIMEFRAME from=$START to=$END"

cur="$START"

while [[ "$cur" < "$END" ]]; do
  next=$(date -I -d "$cur +1 month")
  if [[ "$next" > "$END" ]]; then
    next="$END"
  fi

  echo "MONTHLY_BACKFILL_CHUNK symbol=$SYMBOL timeframe=$TIMEFRAME from=$cur to=$next"

  PYTHONPATH=src /opt/finam-core/venv/bin/python \
    src/scripts/ingestion/backfill_finam_futures_market_bars.py \
    --symbols "$SYMBOL" \
    --timeframe "$TIMEFRAME" \
    --start-date "$cur" \
    --end-date "$next" || true

  cur="$next"
  sleep 1
done

echo "MONTHLY_BACKFILL_DONE symbol=$SYMBOL timeframe=$TIMEFRAME"
