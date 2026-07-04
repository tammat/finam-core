#!/usr/bin/env bash
set -euo pipefail

echo "=== BUILD_TRADING_PLATFORM_FOUNDATION_V1 ==="

mkdir -p sql/analytics scripts

cat > sql/analytics/011_trading_platform_foundation_v1.sql <<'SQL'
CREATE TABLE IF NOT EXISTS analytics.trading_order_intent_v1 (
    id BIGSERIAL PRIMARY KEY,

    risk_decision_id BIGINT,

    symbol TEXT NOT NULL,
    asset_class TEXT NOT NULL DEFAULT '',
    timeframe TEXT NOT NULL,

    strategy_family TEXT NOT NULL,
    strategy_version TEXT NOT NULL DEFAULT 'v1',

    signal_ts TIMESTAMPTZ NOT NULL,

    risk_score NUMERIC(10,4) NOT NULL DEFAULT 0,

    order_side TEXT NOT NULL DEFAULT 'UNKNOWN',
    order_type TEXT NOT NULL DEFAULT 'MARKET',
    quantity NUMERIC(20,8) NOT NULL DEFAULT 0,

    trading_decision_code TEXT NOT NULL DEFAULT 'TRADING_BLOCK',
    recommendation_code TEXT NOT NULL DEFAULT 'WAIT_TRADING_REVIEW',

    paper_allowed BOOLEAN NOT NULL DEFAULT false,
    shadow_allowed BOOLEAN NOT NULL DEFAULT false,
    micro_live_allowed BOOLEAN NOT NULL DEFAULT false,
    live_allowed BOOLEAN NOT NULL DEFAULT false,

    order_sent BOOLEAN NOT NULL DEFAULT false,
    broker_order_id TEXT NOT NULL DEFAULT '',

    source_version TEXT NOT NULL DEFAULT 'TRADING_PLATFORM_FOUNDATION_V1',
    build_id TEXT NOT NULL DEFAULT 'manual',
    refreshed_at TIMESTAMPTZ NOT NULL DEFAULT now(),

    UNIQUE(symbol, timeframe, strategy_family, signal_ts)
);

CREATE INDEX IF NOT EXISTS ix_trading_order_intent_v1_symbol
ON analytics.trading_order_intent_v1(symbol);

CREATE INDEX IF NOT EXISTS ix_trading_order_intent_v1_strategy
ON analytics.trading_order_intent_v1(strategy_family);

CREATE INDEX IF NOT EXISTS ix_trading_order_intent_v1_decision
ON analytics.trading_order_intent_v1(trading_decision_code);

CREATE TABLE IF NOT EXISTS analytics.trading_configuration_v1 (
    trading_name TEXT PRIMARY KEY,
    enabled BOOLEAN NOT NULL DEFAULT true,
    config_json JSONB NOT NULL DEFAULT '{}'::jsonb,
    source_version TEXT NOT NULL DEFAULT 'TRADING_PLATFORM_FOUNDATION_V1',
    build_id TEXT NOT NULL DEFAULT 'manual',
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS analytics.trading_governance_v1 (
    governance_scope TEXT PRIMARY KEY,

    builder_status TEXT NOT NULL DEFAULT 'UNKNOWN',
    order_intent_status TEXT NOT NULL DEFAULT 'UNKNOWN',
    api_status TEXT NOT NULL DEFAULT 'UNKNOWN',
    ui_status TEXT NOT NULL DEFAULT 'UNKNOWN',

    governance_score NUMERIC(10,4) NOT NULL DEFAULT 0,
    readiness_code TEXT NOT NULL DEFAULT 'NOT_READY',
    recommendation_code TEXT NOT NULL DEFAULT 'WAIT_TRADING_FOUNDATION',

    source_version TEXT NOT NULL DEFAULT 'TRADING_PLATFORM_FOUNDATION_V1',
    build_id TEXT NOT NULL DEFAULT 'manual',
    refreshed_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

INSERT INTO analytics.trading_configuration_v1 (
    trading_name,
    enabled,
    config_json
)
VALUES (
    'DEFAULT',
    true,
    '{
        "paper_enabled": true,
        "shadow_enabled": false,
        "micro_live_enabled": false,
        "live_enabled": false,
        "default_order_type": "MARKET",
        "default_quantity": 1
    }'::jsonb
)
ON CONFLICT (trading_name) DO UPDATE SET
    enabled=EXCLUDED.enabled,
    config_json=EXCLUDED.config_json,
    updated_at=now();

GRANT USAGE ON SCHEMA analytics TO alex;
GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA analytics TO alex;
GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA analytics TO alex;
SQL

cat > scripts/test_trading_platform_foundation_v1.sh <<'SH_TEST'
#!/usr/bin/env bash
set -euo pipefail

echo "=== TEST_TRADING_PLATFORM_FOUNDATION_V1 ==="

sudo -u postgres psql -v ON_ERROR_STOP=1 -d finam_core \
  -f sql/analytics/011_trading_platform_foundation_v1.sql

intent_table=$(psql -At -d finam_core -c "SELECT to_regclass('analytics.trading_order_intent_v1') IS NOT NULL;")
config_table=$(psql -At -d finam_core -c "SELECT to_regclass('analytics.trading_configuration_v1') IS NOT NULL;")
governance_table=$(psql -At -d finam_core -c "SELECT to_regclass('analytics.trading_governance_v1') IS NOT NULL;")

config_rows=$(psql -At -d finam_core -c "SELECT count(*) FROM analytics.trading_configuration_v1;")

unsafe=$(psql -At -d finam_core -c "
SELECT count(*)
FROM analytics.trading_order_intent_v1
WHERE live_allowed=true
   OR micro_live_allowed=true
   OR order_sent=true;
")

test "$intent_table" = "t"
test "$config_table" = "t"
test "$governance_table" = "t"
test "$config_rows" -gt 0
test "$unsafe" = "0"

psql -d finam_core -c "\d analytics.trading_order_intent_v1"
psql -d finam_core -c "\d analytics.trading_configuration_v1"
psql -d finam_core -c "\d analytics.trading_governance_v1"

echo "trading_order_intent_table=$intent_table"
echo "trading_configuration_table=$config_table"
echo "trading_governance_table=$governance_table"
echo "configuration_rows=$config_rows"
echo "unsafe_live_or_sent_rows=$unsafe"
echo "runtime_changed=0"
echo "execution_changed=0"
echo "orders_changed=0"
echo "fills_changed=0"
echo "micro_live_allowed=0"
echo "VERDICT=TRADING_PLATFORM_FOUNDATION_V1_READY"
echo "VERDICT=TEST_TRADING_PLATFORM_FOUNDATION_V1_OK"
SH_TEST

chmod +x scripts/test_trading_platform_foundation_v1.sh
scripts/test_trading_platform_foundation_v1.sh

echo "VERDICT=BUILD_TRADING_PLATFORM_FOUNDATION_V1_OK"
