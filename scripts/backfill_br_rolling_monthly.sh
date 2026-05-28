#!/usr/bin/env bash
set -euo pipefail

TIMEFRAME="${1:-M5}"
SLEEP_SEC="${SLEEP_SEC:-1}"

run_contract() {
  local symbol="$1"
  local from="$2"
  local to="$3"

  echo "BR_ROLLING_BACKFILL_CHUNK symbol=${symbol} timeframe=${TIMEFRAME} from=${from} to=${to}"

  PYTHONPATH=src /opt/finam-core/venv/bin/python \
    src/scripts/ingestion/backfill_finam_futures_market_bars.py \
    --symbols "${symbol}@RTSX" \
    --timeframe "$TIMEFRAME" \
    --start-date "$from" \
    --end-date "$to" || true

  sleep "$SLEEP_SEC"
}

# Историческая rolling-загрузка Brent.
# Грузим ближайшие ликвидные контракты по месяцам, а не текущие *6 в прошлое.

run_contract BRM5 2025-05-28 2025-06-01
run_contract BRN5 2025-06-01 2025-07-01
run_contract BRQ5 2025-07-01 2025-08-01
run_contract BRU5 2025-08-01 2025-09-01
run_contract BRV5 2025-09-01 2025-10-01
run_contract BRX5 2025-10-01 2025-11-01
run_contract BRZ5 2025-11-01 2025-12-01
run_contract BRF6 2025-12-01 2026-01-01
run_contract BRG6 2026-01-01 2026-02-01
run_contract BRH6 2026-02-01 2026-03-01
run_contract BRJ6 2026-03-01 2026-04-01
run_contract BRK6 2026-04-01 2026-05-01
run_contract BRM6 2026-05-01 2026-05-28

echo "BR_ROLLING_BACKFILL_DONE timeframe=${TIMEFRAME}"
