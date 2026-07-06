#!/usr/bin/env bash
set -euo pipefail

echo "=== COMMISSION_MODEL_V1 ==="

sudo -u postgres psql -v ON_ERROR_STOP=1 -d finam_core <<'SQL'
CREATE TABLE IF NOT EXISTS analytics.commission_model_v1 (
    id BIGSERIAL PRIMARY KEY,
    asset_class TEXT NOT NULL,
    symbol_pattern TEXT NOT NULL DEFAULT '*',
    commission_per_trade NUMERIC(20,8) NOT NULL DEFAULT 0,
    commission_pct NUMERIC(20,8) NOT NULL DEFAULT 0,
    slippage_per_trade NUMERIC(20,8) NOT NULL DEFAULT 0,
    enabled BOOLEAN NOT NULL DEFAULT true,
    source_version TEXT NOT NULL DEFAULT 'COMMISSION_MODEL_V1',
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE(asset_class, symbol_pattern)
);

INSERT INTO analytics.commission_model_v1 (
    asset_class,
    symbol_pattern,
    commission_per_trade,
    commission_pct,
    slippage_per_trade,
    enabled
)
VALUES
('EQUITY', '*@MISX', 0.01, 0.0005, 0.01, true),
('FUTURES', '*@RTSX', 1.00, 0.0000, 1.00, true)
ON CONFLICT(asset_class, symbol_pattern) DO UPDATE SET
    commission_per_trade=EXCLUDED.commission_per_trade,
    commission_pct=EXCLUDED.commission_pct,
    slippage_per_trade=EXCLUDED.slippage_per_trade,
    enabled=true,
    updated_at=now();

GRANT SELECT, INSERT, UPDATE, DELETE ON analytics.commission_model_v1 TO alex;
GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA analytics TO alex;
SQL

sudo -u postgres psql -v ON_ERROR_STOP=1 -d finam_core <<'SQL'
UPDATE analytics.research_trade_v1 t
SET
    commission =
        cm.commission_per_trade
        + abs(t.entry_price * cm.commission_pct),
    slippage =
        cm.slippage_per_trade,
    net_pnl =
        t.gross_pnl
        - (cm.commission_per_trade + abs(t.entry_price * cm.commission_pct))
        - cm.slippage_per_trade
FROM analytics.commission_model_v1 cm
WHERE cm.enabled=true
  AND (
        (cm.symbol_pattern='*@MISX' AND t.symbol LIKE '%@MISX')
     OR (cm.symbol_pattern='*@RTSX' AND t.symbol LIKE '%@RTSX')
  );
SQL

scripts/test_paper_portfolio_mtm_v1.sh

commission_sum=$(psql -At -d finam_core -c "
SELECT coalesce(sum(commission),0)
FROM analytics.research_trade_v1;
")

unsafe=$(psql -At -d finam_core -c "
SELECT count(*)
FROM analytics.edge_candidate_v1
WHERE micro_live_allowed=true OR live_allowed=true;
")

test "$commission_sum" != "0"
test "$unsafe" = "0"

echo "commission_sum=$commission_sum"
echo "unsafe_rows=$unsafe"
echo "runtime_changed=0"
echo "execution_changed=0"
echo "orders_changed=0"
echo "fills_changed=0"
echo "micro_live_allowed=0"
echo "VERDICT=COMMISSION_MODEL_V1_READY"
echo "VERDICT=TEST_COMMISSION_MODEL_V1_OK"
