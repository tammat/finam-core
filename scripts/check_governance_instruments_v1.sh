#!/usr/bin/env bash
set -euo pipefail

cd /opt/finam-core
set -a
. /opt/finam-core/.env
set +a

echo "=== GOVERNANCE SYMBOLS ==="
psql "$DATABASE_URL" -c "
SELECT
  symbol,
  side,
  COUNT(*) AS rows,
  SUM(CASE WHEN allowed THEN 1 ELSE 0 END) AS allowed_rows,
  SUM(CASE WHEN NOT allowed THEN 1 ELSE 0 END) AS blocked_rows,
  ROUND(AVG(expectancy_points)::numeric, 6) AS avg_expectancy,
  MAX(created_at) AS last_ts
FROM runtime_governance_live_accumulation_v1
WHERE symbol ~ '^(BR|NG|USD|USDRUB)'
GROUP BY symbol, side
ORDER BY rows DESC;
"

echo "=== TRADES SYMBOLS ==="
psql "$DATABASE_URL" -c "
SELECT
  symbol,
  side,
  COUNT(*) AS trades,
  SUM(qty) AS qty_sum,
  ROUND(SUM(commission)::numeric, 4) AS commission_sum,
  MAX(created_at) AS last_trade
FROM trades
WHERE symbol ~ '^(BR|NG|USD|USDRUB)'
GROUP BY symbol, side
ORDER BY trades DESC;
"

echo "=== CLOSED TRADES SYMBOLS ==="
psql "$DATABASE_URL" -c "
SELECT
  symbol,
  side,
  COUNT(*) AS closed_trades,
  ROUND(SUM(gross_pnl)::numeric, 4) AS gross_pnl_sum,
  ROUND(SUM(net_pnl)::numeric, 4) AS net_pnl_sum,
  ROUND(AVG(net_pnl)::numeric, 6) AS avg_net_pnl,
  ROUND(SUM(commission)::numeric, 4) AS commission_sum,
  MAX(COALESCE(closed_at, exit_ts, created_at)) AS last_closed
FROM closed_trades
WHERE symbol ~ '^(BR|NG|USD|USDRUB)'
GROUP BY symbol, side
ORDER BY closed_trades DESC;
"
