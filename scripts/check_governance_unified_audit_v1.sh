#!/usr/bin/env bash
set -euo pipefail

cd /opt/finam-core
set -a
. /opt/finam-core/.env
set +a

echo "=== BR/USD COMMON GOVERNANCE ==="
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
WHERE symbol ~ '^(BR|USD|USDRUB)'
GROUP BY symbol, side
ORDER BY rows DESC;
"

echo "=== NG LIVE RUNTIME STATE ==="
psql "$DATABASE_URL" -c "
SELECT
  symbol,
  strategy,
  timeframe,
  runtime_state,
  allow_new_entries,
  governance_allow,
  market_data_fresh,
  active_edge,
  open_position_qty,
  state_reason,
  updated_at
FROM ng_live_runtime_state
ORDER BY updated_at DESC;
"

echo "=== NG ACTIVE EDGE STATE ==="
psql "$DATABASE_URL" -c "
SELECT
  symbol,
  strategy,
  timeframe,
  current_session,
  required_regime_v2,
  governance_decision,
  governance_allow_runtime,
  policy_matched,
  active_edge,
  reason,
  calculated_at
FROM ng_active_edge_state
ORDER BY calculated_at DESC;
"

echo "=== NG M1 POLICY ALLOW ==="
psql "$DATABASE_URL" -c "
SELECT
  symbol,
  session_bucket,
  regime_v2,
  allow_runtime,
  trades,
  ROUND(profit_factor::numeric, 4) AS pf,
  ROUND(expectancy::numeric, 6) AS expectancy,
  ROUND(winrate::numeric, 4) AS winrate,
  calculated_at
FROM ng_m1_runtime_policy
WHERE allow_runtime = true
ORDER BY calculated_at DESC, symbol;
"

echo "=== CLOSED TRADES BR/USD/NG ==="
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
ORDER BY net_pnl_sum DESC;
"
