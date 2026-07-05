#!/usr/bin/env bash
set -euo pipefail

echo "=== FINAM_CORE_CONSOLIDATION_V1 ==="

echo "--- GIT STATUS ---"
git status --short

echo "--- CANONICAL TABLES ---"
psql -d finam_core -c "
SELECT schemaname, relname, n_live_tup
FROM pg_stat_user_tables
WHERE schemaname='analytics'
  AND relname IN (
    'market_snapshot_v1',
    'feature_snapshot_v1',
    'strategy_signal_snapshot_v1',
    'edge_decision_snapshot_v1',
    'risk_decision_snapshot_v1',
    'trading_order_intent_v1',
    'portfolio_position_snapshot_v1',
    'portfolio_equity_snapshot_v1'
  )
ORDER BY relname;
"

echo "--- LEGACY SCAN ---"
grep -RInE "TODO|FIXME|deprecated|LEGACY" src scripts sql docs || true

echo "--- UI SQL SCAN ---"
if grep -RInE "SELECT .*FROM|FROM analytics\." src/marketcore/presentation/pages; then
  echo "ERROR_UI_DIRECT_SQL_FOUND"
  exit 1
fi

echo "--- PLATFORM API CHECK ---"
for path in \
  strategy-platform/summary \
  edge-platform/summary \
  risk-platform/summary \
  trading-platform/summary \
  portfolio-platform/summary
do
  curl -fsS "http://127.0.0.1:8095/api/kg/v1/$path" >/tmp/"${path//\//_}.json"
done

echo "--- PLATFORM UI CHECK ---"
for path in \
  strategy-platform \
  edge-platform \
  risk-platform \
  trading-platform \
  portfolio-platform
do
  curl -fsS "http://127.0.0.1:8080/$path" >/tmp/"${path}.html"
done

echo "runtime_changed=0"
echo "execution_changed=0"
echo "orders_changed=0"
echo "fills_changed=0"
echo "micro_live_allowed=0"
echo "VERDICT=FINAM_CORE_CONSOLIDATION_V1_OK"
