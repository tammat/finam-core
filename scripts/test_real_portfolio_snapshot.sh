#!/usr/bin/env bash
set -euo pipefail

export PYTHONPATH=src
export DATABASE_URL="${DATABASE_URL:-postgresql://finam:finam@localhost:5432/finam_core}"

TMP="/tmp/real_portfolio_test.json"

cat > "$TMP" <<'JSON'
[
  {
    "symbol": "BRM6@RTSX",
    "qty": 1,
    "avg_price": 80,
    "current_price": 82,
    "market_value": 8200,
    "pnl": 200,
    "pnl_day": 50,
    "currency": "RUB"
  }
]
JSON

REAL_PORTFOLIO_JSON="$TMP" bash scripts/sync_real_portfolio_snapshot.sh

psql "$DATABASE_URL" -c "SELECT * FROM v_real_portfolio_positions_ru WHERE \"Тикер\" = 'BRM6@RTSX';" | grep -q "BRM6@RTSX"

echo "REAL_PORTFOLIO_SNAPSHOT_TEST_OK"
