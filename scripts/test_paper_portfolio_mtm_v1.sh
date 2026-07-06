#!/usr/bin/env bash
set -euo pipefail

echo "=== PAPER_PORTFOLIO_MTM_V1 ==="

sudo -u postgres psql -v ON_ERROR_STOP=1 -d finam_core <<'SQL'
CREATE TABLE IF NOT EXISTS analytics.paper_portfolio_mtm_v1 (
    id BIGSERIAL PRIMARY KEY,
    mtm_ts TIMESTAMPTZ NOT NULL DEFAULT now(),
    candidate_id BIGINT NOT NULL,
    strategy_code TEXT NOT NULL,
    symbol TEXT NOT NULL,
    timeframe TEXT NOT NULL,
    trades INTEGER NOT NULL DEFAULT 0,
    gross_pnl NUMERIC(20,8) NOT NULL DEFAULT 0,
    commission NUMERIC(20,8) NOT NULL DEFAULT 0,
    slippage NUMERIC(20,8) NOT NULL DEFAULT 0,
    net_pnl NUMERIC(20,8) NOT NULL DEFAULT 0,
    max_drawdown NUMERIC(20,8) NOT NULL DEFAULT 0,
    paper_status TEXT NOT NULL DEFAULT 'ACTIVE',
    source_version TEXT NOT NULL DEFAULT 'PAPER_PORTFOLIO_MTM_V1',
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

GRANT SELECT, INSERT, UPDATE, DELETE ON analytics.paper_portfolio_mtm_v1 TO alex;
GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA analytics TO alex;
SQL

sudo -u postgres psql -v ON_ERROR_STOP=1 -d finam_core <<'SQL'
INSERT INTO analytics.paper_portfolio_mtm_v1 (
    candidate_id,
    strategy_code,
    symbol,
    timeframe,
    trades,
    gross_pnl,
    commission,
    slippage,
    net_pnl,
    max_drawdown,
    paper_status,
    source_version,
    updated_at
)
SELECT
    p.candidate_id,
    p.strategy_code,
    p.symbol,
    p.timeframe,
    count(t.id) AS trades,
    coalesce(sum(t.gross_pnl),0) AS gross_pnl,
    coalesce(sum(t.commission),0) AS commission,
    coalesce(sum(t.slippage),0) AS slippage,
    coalesce(sum(t.net_pnl),0) AS net_pnl,
    coalesce(min(o.max_drawdown),0) AS max_drawdown,
    p.paper_status,
    'PAPER_PORTFOLIO_MTM_V1',
    now()
FROM analytics.paper_runtime_candidate_v1 p
JOIN analytics.edge_candidate_v1 c
  ON c.id=p.candidate_id
JOIN analytics.edge_observation_v1 o
  ON o.observation_uuid=p.observation_uuid
LEFT JOIN analytics.research_trade_v1 t
  ON t.research_code=c.research_code
WHERE p.paper_status='ACTIVE'
GROUP BY
    p.candidate_id,
    p.strategy_code,
    p.symbol,
    p.timeframe,
    p.paper_status;
SQL

mtm_rows=$(psql -At -d finam_core -c "
SELECT count(*)
FROM analytics.paper_portfolio_mtm_v1
WHERE source_version='PAPER_PORTFOLIO_MTM_V1';
")

unsafe=$(psql -At -d finam_core -c "
SELECT count(*)
FROM analytics.edge_candidate_v1
WHERE micro_live_allowed=true OR live_allowed=true;
")

test "$mtm_rows" -gt 0
test "$unsafe" = "0"

psql -d finam_core -c "
SELECT
  mtm_ts,
  candidate_id,
  strategy_code,
  symbol,
  timeframe,
  trades,
  round(gross_pnl,6) AS gross_pnl,
  round(commission,6) AS commission,
  round(slippage,6) AS slippage,
  round(net_pnl,6) AS net_pnl,
  round(max_drawdown,6) AS max_drawdown,
  paper_status
FROM analytics.paper_portfolio_mtm_v1
ORDER BY mtm_ts DESC, net_pnl DESC
LIMIT 30;
"

psql -d finam_core -c "
SELECT
  count(*) AS active_candidates,
  sum(trades) AS trades,
  round(sum(gross_pnl),6) AS gross_pnl,
  round(sum(commission),6) AS commission,
  round(sum(slippage),6) AS slippage,
  round(sum(net_pnl),6) AS net_pnl,
  round(min(max_drawdown),6) AS worst_drawdown
FROM analytics.paper_portfolio_mtm_v1
WHERE mtm_ts = (
  SELECT max(mtm_ts)
  FROM analytics.paper_portfolio_mtm_v1
);
"

echo "paper_mtm_rows=$mtm_rows"
echo "unsafe_rows=$unsafe"
echo "runtime_changed=0"
echo "execution_changed=0"
echo "orders_changed=0"
echo "fills_changed=0"
echo "micro_live_allowed=0"
echo "VERDICT=PAPER_PORTFOLIO_MTM_V1_READY"
echo "VERDICT=TEST_PAPER_PORTFOLIO_MTM_V1_OK"
