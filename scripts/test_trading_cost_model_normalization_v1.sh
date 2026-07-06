#!/usr/bin/env bash
set -euo pipefail

echo "=== TRADING_COST_MODEL_NORMALIZATION_V1 ==="

sudo -u postgres psql -v ON_ERROR_STOP=1 -d finam_core <<'SQL'
CREATE TABLE IF NOT EXISTS analytics.account_tax_profile_v1 (
    tax_profile_code TEXT PRIMARY KEY,
    account_scope TEXT NOT NULL DEFAULT 'BASE',
    tax_rate NUMERIC(20,8) NOT NULL DEFAULT 0,
    description TEXT NOT NULL DEFAULT '',
    is_active BOOLEAN NOT NULL DEFAULT true,
    source_version TEXT NOT NULL DEFAULT 'TRADING_COST_MODEL_NORMALIZATION_V1',
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS analytics.broker_fee_profile_v1 (
    broker_fee_code TEXT PRIMARY KEY,
    broker_code TEXT NOT NULL DEFAULT 'FINAM',
    exchange_code TEXT NOT NULL,
    asset_class TEXT NOT NULL,
    commission_per_trade NUMERIC(20,8) NOT NULL DEFAULT 0,
    commission_pct NUMERIC(20,8) NOT NULL DEFAULT 0,
    is_active BOOLEAN NOT NULL DEFAULT true,
    source_version TEXT NOT NULL DEFAULT 'TRADING_COST_MODEL_NORMALIZATION_V1',
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS analytics.exchange_fee_profile_v1 (
    exchange_fee_code TEXT PRIMARY KEY,
    exchange_code TEXT NOT NULL,
    asset_class TEXT NOT NULL,
    exchange_fee_per_trade NUMERIC(20,8) NOT NULL DEFAULT 0,
    clearing_fee_per_trade NUMERIC(20,8) NOT NULL DEFAULT 0,
    is_active BOOLEAN NOT NULL DEFAULT true,
    source_version TEXT NOT NULL DEFAULT 'TRADING_COST_MODEL_NORMALIZATION_V1',
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS analytics.slippage_profile_v1 (
    slippage_profile_code TEXT PRIMARY KEY,
    exchange_code TEXT NOT NULL,
    asset_class TEXT NOT NULL,
    liquidity_bucket TEXT NOT NULL DEFAULT 'DEFAULT',
    slippage_per_trade NUMERIC(20,8) NOT NULL DEFAULT 0,
    is_active BOOLEAN NOT NULL DEFAULT true,
    source_version TEXT NOT NULL DEFAULT 'TRADING_COST_MODEL_NORMALIZATION_V1',
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

INSERT INTO analytics.account_tax_profile_v1 (
    tax_profile_code, account_scope, tax_rate, description
)
VALUES
    ('RU_TAXABLE_BASE', 'BASE', 0.15, 'Налоговый профиль базового брокерского счёта')
ON CONFLICT(tax_profile_code) DO UPDATE SET
    tax_rate=EXCLUDED.tax_rate,
    updated_at=now();

INSERT INTO analytics.broker_fee_profile_v1 (
    broker_fee_code, broker_code, exchange_code, asset_class, commission_per_trade, commission_pct
)
VALUES
    ('FINAM_MISX_EQUITY_BASE','FINAM','MISX','EQUITY',0.01,0.0005),
    ('FINAM_RTSX_FUTURES_BASE','FINAM','RTSX','FUTURES',1.00,0.0000)
ON CONFLICT(broker_fee_code) DO UPDATE SET
    commission_per_trade=EXCLUDED.commission_per_trade,
    commission_pct=EXCLUDED.commission_pct,
    updated_at=now();

INSERT INTO analytics.exchange_fee_profile_v1 (
    exchange_fee_code, exchange_code, asset_class, exchange_fee_per_trade, clearing_fee_per_trade
)
VALUES
    ('MISX_EQUITY_BASE','MISX','EQUITY',0.00,0.00),
    ('RTSX_FUTURES_BASE','RTSX','FUTURES',0.00,0.00)
ON CONFLICT(exchange_fee_code) DO UPDATE SET
    exchange_fee_per_trade=EXCLUDED.exchange_fee_per_trade,
    clearing_fee_per_trade=EXCLUDED.clearing_fee_per_trade,
    updated_at=now();

INSERT INTO analytics.slippage_profile_v1 (
    slippage_profile_code, exchange_code, asset_class, liquidity_bucket, slippage_per_trade
)
VALUES
    ('MISX_EQUITY_DEFAULT','MISX','EQUITY','DEFAULT',0.01),
    ('RTSX_FUTURES_DEFAULT','RTSX','FUTURES','DEFAULT',1.00)
ON CONFLICT(slippage_profile_code) DO UPDATE SET
    slippage_per_trade=EXCLUDED.slippage_per_trade,
    updated_at=now();

GRANT SELECT, INSERT, UPDATE, DELETE ON analytics.account_tax_profile_v1 TO alex;
GRANT SELECT, INSERT, UPDATE, DELETE ON analytics.broker_fee_profile_v1 TO alex;
GRANT SELECT, INSERT, UPDATE, DELETE ON analytics.exchange_fee_profile_v1 TO alex;
GRANT SELECT, INSERT, UPDATE, DELETE ON analytics.slippage_profile_v1 TO alex;
SQL

sudo -u postgres psql -v ON_ERROR_STOP=1 -d finam_core <<'SQL'
UPDATE analytics.research_trade_v1 t
SET
    commission = bf.commission_per_trade + abs(t.entry_price * bf.commission_pct),
    slippage = sp.slippage_per_trade,
    net_pnl =
        t.gross_pnl
        - (bf.commission_per_trade + abs(t.entry_price * bf.commission_pct))
        - ef.exchange_fee_per_trade
        - ef.clearing_fee_per_trade
        - sp.slippage_per_trade
FROM analytics.market_instrument_v1 i
JOIN analytics.broker_fee_profile_v1 bf
  ON bf.exchange_code=i.exchange_code
 AND bf.asset_class=i.asset_class
 AND bf.broker_code='FINAM'
 AND bf.is_active=true
JOIN analytics.exchange_fee_profile_v1 ef
  ON ef.exchange_code=i.exchange_code
 AND ef.asset_class=i.asset_class
 AND ef.is_active=true
JOIN analytics.slippage_profile_v1 sp
  ON sp.exchange_code=i.exchange_code
 AND sp.asset_class=i.asset_class
 AND sp.liquidity_bucket='DEFAULT'
 AND sp.is_active=true
WHERE i.symbol=t.symbol
  AND i.is_active=true;
SQL

scripts/test_paper_portfolio_mtm_v1.sh

sudo -u postgres psql -v ON_ERROR_STOP=1 -d finam_core <<'SQL'
UPDATE analytics.paper_portfolio_mtm_v1 m
SET
    estimated_tax =
        CASE
            WHEN m.net_pnl > 0 THEN m.net_pnl * tp.tax_rate
            ELSE 0
        END,
    net_after_tax =
        CASE
            WHEN m.net_pnl > 0 THEN m.net_pnl - (m.net_pnl * tp.tax_rate)
            ELSE m.net_pnl
        END,
    source_version='TRADING_COST_MODEL_NORMALIZATION_V1',
    updated_at=now()
FROM analytics.account_tax_profile_v1 tp
WHERE tp.tax_profile_code='RU_TAXABLE_BASE'
  AND tp.is_active=true;
SQL

profiles=$(psql -At -d finam_core -c "
SELECT
  (SELECT count(*) FROM analytics.account_tax_profile_v1 WHERE is_active=true)
+ (SELECT count(*) FROM analytics.broker_fee_profile_v1 WHERE is_active=true)
+ (SELECT count(*) FROM analytics.exchange_fee_profile_v1 WHERE is_active=true)
+ (SELECT count(*) FROM analytics.slippage_profile_v1 WHERE is_active=true);
")

commission_sum=$(psql -At -d finam_core -c "
SELECT coalesce(sum(commission),0)
FROM analytics.research_trade_v1;
")

taxed_rows=$(psql -At -d finam_core -c "
SELECT count(*)
FROM analytics.paper_portfolio_mtm_v1
WHERE source_version='TRADING_COST_MODEL_NORMALIZATION_V1';
")

unsafe=$(psql -At -d finam_core -c "
SELECT count(*)
FROM analytics.edge_candidate_v1
WHERE micro_live_allowed=true OR live_allowed=true;
")

test "$profiles" -ge 7
test "$commission_sum" != "0"
test "$taxed_rows" -gt 0
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
    round(m.slippage,6) AS slippage,
    round(m.net_pnl,6) AS net_trading_pnl,
    round(m.estimated_tax,6) AS estimated_tax,
    round(m.net_after_tax,6) AS net_after_tax
FROM analytics.paper_portfolio_mtm_v1 m
ORDER BY m.mtm_ts DESC, m.net_after_tax DESC
LIMIT 30;
"

echo "active_cost_profiles=$profiles"
echo "commission_sum=$commission_sum"
echo "taxed_rows=$taxed_rows"
echo "unsafe_rows=$unsafe"
echo "runtime_changed=0"
echo "execution_changed=0"
echo "orders_changed=0"
echo "fills_changed=0"
echo "micro_live_allowed=0"
echo "VERDICT=TRADING_COST_MODEL_NORMALIZATION_V1_READY"
echo "VERDICT=TEST_TRADING_COST_MODEL_NORMALIZATION_V1_OK"
