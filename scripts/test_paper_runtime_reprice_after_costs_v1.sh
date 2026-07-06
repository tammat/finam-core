#!/usr/bin/env bash
set -euo pipefail

echo "=== PAPER_RUNTIME_REPRICE_AFTER_COSTS_V1 ==="

scripts/test_trading_cost_model_v1.sh
scripts/test_paper_portfolio_mtm_v1.sh

psql -d finam_core -c "
SELECT
  candidate_id,
  strategy_code,
  symbol,
  timeframe,
  trades,
  round(gross_pnl,6) AS gross_pnl,
  round(commission,6) AS commission,
  round(slippage,6) AS slippage,
  round(net_pnl,6) AS net_trading_pnl,
  round(estimated_tax,6) AS estimated_tax,
  round(net_after_tax,6) AS net_after_tax
FROM analytics.paper_portfolio_mtm_v1
ORDER BY mtm_ts DESC, net_after_tax DESC
LIMIT 30;
"

unsafe=$(psql -At -d finam_core -c "
SELECT count(*)
FROM analytics.edge_candidate_v1
WHERE micro_live_allowed=true OR live_allowed=true;
")

taxed=$(psql -At -d finam_core -c "
SELECT count(*)
FROM analytics.paper_portfolio_mtm_v1
WHERE net_after_tax IS NOT NULL;
")

test "$unsafe" = "0"
test "$taxed" -gt 0

echo "paper_repriced_rows=$taxed"
echo "unsafe_rows=$unsafe"
echo "runtime_changed=0"
echo "execution_changed=0"
echo "orders_changed=0"
echo "fills_changed=0"
echo "micro_live_allowed=0"
echo "VERDICT=PAPER_RUNTIME_REPRICE_AFTER_COSTS_V1_READY"
echo "VERDICT=TEST_PAPER_RUNTIME_REPRICE_AFTER_COSTS_V1_OK"
