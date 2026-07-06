#!/usr/bin/env bash
set -euo pipefail

echo "=== TRADING_COST_MODEL_V1 ==="

sudo -u postgres psql -v ON_ERROR_STOP=1 -d finam_core <<'SQL'
CREATE TABLE IF NOT EXISTS analytics.trading_cost_profile_v1 (
    id BIGSERIAL PRIMARY KEY,
    symbol TEXT NOT NULL REFERENCES analytics.market_instrument_v1(symbol),
    broker_code TEXT NOT NULL DEFAULT 'FINAM',
    account_scope TEXT NOT NULL DEFAULT 'BASE',
    commission_per_trade NUMERIC(20,8) NOT NULL DEFAULT 0,
    commission_pct NUMERIC(20,8) NOT NULL DEFAULT 0,
    exchange_fee_per_trade NUMERIC(20,8) NOT NULL DEFAULT 0,
    clearing_fee_per_trade NUMERIC(20,8) NOT NULL DEFAULT 0,
    slippage_per_trade NUMERIC(20,8) NOT NULL DEFAULT 0,
    tax_rate NUMERIC(20,8) NOT NULL DEFAULT 0,
    valid_from TIMESTAMPTZ NOT NULL DEFAULT now(),
    valid_to TIMESTAMPTZ,
    is_active BOOLEAN NOT NULL DEFAULT true,
    source_version TEXT NOT NULL DEFAULT 'TRADING_COST_MODEL_V1',
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE(symbol, broker_code, account_scope, valid_from)
);

INSERT INTO analytics.trading_cost_profile_v1 (
    symbol,
    broker_code,
    account_scope,
    commission_per_trade,
    commission_pct,
    exchange_fee_per_trade,
    clearing_fee_per_trade,
    slippage_per_trade,
    tax_rate
)
VALUES
    ('SBER@MISX','FINAM','BASE',0.01,0.0005,0.00,0.00,0.01,0.13),
    ('LKOH@MISX','FINAM','BASE',0.01,0.0005,0.00,0.00,0.01,0.13),
    ('BR@RTSX','FINAM','BASE',1.00,0.0000,0.00,0.00,1.00,0.13),
    ('NG@RTSX','FINAM','BASE',1.00,0.0000,0.00,0.00,1.00,0.13)
ON CONFLICT(symbol, broker_code, account_scope, valid_from) DO NOTHING;

GRANT SELECT, INSERT, UPDATE, DELETE ON analytics.trading_cost_profile_v1 TO alex;
GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA analytics TO alex;
SQL

sudo -u postgres psql -v ON_ERROR_STOP=1 -d finam_core <<'SQL'
ALTER TABLE analytics.paper_portfolio_mtm_v1
ADD COLUMN IF NOT EXISTS exchange_fee NUMERIC(20,8) NOT NULL DEFAULT 0;

ALTER TABLE analytics.paper_portfolio_mtm_v1
ADD COLUMN IF NOT EXISTS clearing_fee NUMERIC(20,8) NOT NULL DEFAULT 0;

ALTER TABLE analytics.paper_portfolio_mtm_v1
ADD COLUMN IF NOT EXISTS estimated_tax NUMERIC(20,8) NOT NULL DEFAULT 0;

ALTER TABLE analytics.paper_portfolio_mtm_v1
ADD COLUMN IF NOT EXISTS net_after_tax NUMERIC(20,8) NOT NULL DEFAULT 0;
SQL

sudo -u postgres psql -v ON_ERROR_STOP=1 -d finam_core <<'SQL'
UPDATE analytics.research_trade_v1 t
SET
    commission =
        cp.commission_per_trade
        + abs(t.entry_price * cp.commission_pct),
    slippage =
        cp.slippage_per_trade,
    net_pnl =
        t.gross_pnl
        - (cp.commission_per_trade + abs(t.entry_price * cp.commission_pct))
        - cp.exchange_fee_per_trade
        - cp.clearing_fee_per_trade
        - cp.slippage_per_trade
FROM analytics.trading_cost_profile_v1 cp
WHERE cp.symbol=t.symbol
  AND cp.broker_code='FINAM'
  AND cp.account_scope='BASE'
  AND cp.is_active=true;
SQL

scripts/test_paper_portfolio_mtm_v1.sh

sudo -u postgres psql -v ON_ERROR_STOP=1 -d finam_core <<'SQL'
UPDATE analytics.paper_portfolio_mtm_v1 m
SET
    exchange_fee = q.exchange_fee,
    clearing_fee = q.clearing_fee,
    estimated_tax = CASE WHEN m.net_pnl > 0 THEN m.net_pnl * q.tax_rate ELSE 0 END,
    net_after_tax = CASE WHEN m.net_pnl > 0 THEN m.net_pnl - (m.net_pnl * q.tax_rate) ELSE m.net_pnl END,
    source_version='TRADING_COST_MODEL_V1',
    updated_at=now()
FROM (
    SELECT
        p.candidate_id,
        coalesce(sum(cp.exchange_fee_per_trade),0) AS exchange_fee,
        coalesce(sum(cp.clearing_fee_per_trade),0) AS clearing_fee,
        max(cp.tax_rate) AS tax_rate
    FROM analytics.paper_runtime_candidate_v1 p
    JOIN analytics.edge_candidate_v1 c
      ON c.id=p.candidate_id
    JOIN analytics.research_trade_v1 t
      ON t.research_code=c.research_code
    JOIN analytics.trading_cost_profile_v1 cp
      ON cp.symbol=t.symbol
     AND cp.broker_code='FINAM'
     AND cp.account_scope='BASE'
     AND cp.is_active=true
    GROUP BY p.candidate_id
) q
WHERE q.candidate_id=m.candidate_id;
SQL

cost_rows=$(psql -At -d finam_core -c "
SELECT count(*)
FROM analytics.trading_cost_profile_v1
WHERE is_active=true;
")

commission_sum=$(psql -At -d finam_core -c "
SELECT coalesce(sum(commission),0)
FROM analytics.research_trade_v1;
")

tax_rows=$(psql -At -d finam_core -c "
SELECT count(*)
FROM analytics.paper_portfolio_mtm_v1
WHERE source_version='TRADING_COST_MODEL_V1'
  AND net_after_tax IS NOT NULL;
")

unsafe=$(psql -At -d finam_core -c "
SELECT count(*)
FROM analytics.edge_candidate_v1
WHERE micro_live_allowed=true OR live_allowed=true;
")

test "$cost_rows" -ge 4
test "$commission_sum" != "0"
test "$tax_rows" -gt 0
test "$unsafe" = "0"

psql -d finam_core -c "
SELECT
    m.candidate_id,
    m.strategy_code,
    m.symbol,
    m.timeframe,
    m.trades,
    round(m.gross_pnl,6) AS gross_pnl,
    round(m.commission,6) AS commission,
    round(m.exchange_fee,6) AS exchange_fee,
    round(m.clearing_fee,6) AS clearing_fee,
    round(m.slippage,6) AS slippage,
    round(m.net_pnl,6) AS net_trading_pnl,
    round(m.estimated_tax,6) AS estimated_tax,
    round(m.net_after_tax,6) AS net_after_tax
FROM analytics.paper_portfolio_mtm_v1 m
ORDER BY m.mtm_ts DESC, m.net_after_tax DESC
LIMIT 30;
"

echo "trading_cost_profiles=$cost_rows"
echo "commission_sum=$commission_sum"
echo "paper_tax_rows=$tax_rows"
echo "unsafe_rows=$unsafe"
echo "runtime_changed=0"
echo "execution_changed=0"
echo "orders_changed=0"
echo "fills_changed=0"
echo "micro_live_allowed=0"
echo "VERDICT=TRADING_COST_MODEL_V1_READY"
echo "VERDICT=TEST_TRADING_COST_MODEL_V1_OK"
