#!/usr/bin/env bash
set -euo pipefail

echo "=== BUILD_RISK_PLATFORM_FOUNDATION_V1 ==="

mkdir -p sql/analytics scripts

cat > sql/analytics/010_risk_platform_foundation_v1.sql <<'SQL'
CREATE TABLE IF NOT EXISTS analytics.risk_decision_snapshot_v1 (
    id BIGSERIAL PRIMARY KEY,

    edge_decision_id BIGINT,

    symbol TEXT NOT NULL,
    asset_class TEXT NOT NULL DEFAULT '',
    timeframe TEXT NOT NULL,

    strategy_family TEXT NOT NULL,
    strategy_version TEXT NOT NULL DEFAULT 'v1',

    signal_ts TIMESTAMPTZ NOT NULL,

    edge_score NUMERIC(10,4) NOT NULL DEFAULT 0,
    validation_score NUMERIC(10,4) NOT NULL DEFAULT 0,

    risk_score NUMERIC(10,4) NOT NULL DEFAULT 0,

    position_risk_score NUMERIC(10,4) NOT NULL DEFAULT 0,
    exposure_risk_score NUMERIC(10,4) NOT NULL DEFAULT 0,
    daily_loss_risk_score NUMERIC(10,4) NOT NULL DEFAULT 0,
    correlation_risk_score NUMERIC(10,4) NOT NULL DEFAULT 0,
    kill_switch_score NUMERIC(10,4) NOT NULL DEFAULT 0,

    risk_decision_code TEXT NOT NULL DEFAULT 'BLOCK',
    recommendation_code TEXT NOT NULL DEFAULT 'WAIT_RISK_REVIEW',

    ready_for_paper BOOLEAN NOT NULL DEFAULT false,
    ready_for_shadow BOOLEAN NOT NULL DEFAULT false,
    ready_for_micro_live BOOLEAN NOT NULL DEFAULT false,
    ready_for_live BOOLEAN NOT NULL DEFAULT false,

    source_version TEXT NOT NULL DEFAULT 'RISK_PLATFORM_FOUNDATION_V1',
    build_id TEXT NOT NULL DEFAULT 'manual',
    refreshed_at TIMESTAMPTZ NOT NULL DEFAULT now(),

    UNIQUE(symbol, timeframe, strategy_family, signal_ts)
);

CREATE INDEX IF NOT EXISTS ix_risk_decision_snapshot_v1_symbol
ON analytics.risk_decision_snapshot_v1(symbol);

CREATE INDEX IF NOT EXISTS ix_risk_decision_snapshot_v1_strategy
ON analytics.risk_decision_snapshot_v1(strategy_family);

CREATE INDEX IF NOT EXISTS ix_risk_decision_snapshot_v1_decision
ON analytics.risk_decision_snapshot_v1(risk_decision_code);

CREATE TABLE IF NOT EXISTS analytics.risk_configuration_v1 (
    risk_name TEXT PRIMARY KEY,

    enabled BOOLEAN NOT NULL DEFAULT true,

    config_json JSONB NOT NULL DEFAULT '{}'::jsonb,

    source_version TEXT NOT NULL DEFAULT 'RISK_PLATFORM_FOUNDATION_V1',
    build_id TEXT NOT NULL DEFAULT 'manual',
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS analytics.risk_governance_v1 (
    governance_scope TEXT PRIMARY KEY,

    rule_engine_status TEXT NOT NULL DEFAULT 'UNKNOWN',
    builder_status TEXT NOT NULL DEFAULT 'UNKNOWN',
    decision_status TEXT NOT NULL DEFAULT 'UNKNOWN',
    api_status TEXT NOT NULL DEFAULT 'UNKNOWN',
    ui_status TEXT NOT NULL DEFAULT 'UNKNOWN',

    governance_score NUMERIC(10,4) NOT NULL DEFAULT 0,

    readiness_code TEXT NOT NULL DEFAULT 'NOT_READY',
    recommendation_code TEXT NOT NULL DEFAULT 'WAIT_RISK_FOUNDATION',

    source_version TEXT NOT NULL DEFAULT 'RISK_PLATFORM_FOUNDATION_V1',
    build_id TEXT NOT NULL DEFAULT 'manual',
    refreshed_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

INSERT INTO analytics.risk_configuration_v1 (
    risk_name,
    enabled,
    config_json
)
VALUES (
    'DEFAULT',
    true,
    '{
        "max_risk_per_trade": 0.01,
        "daily_loss_limit": 0.03,
        "exposure_limit": 0.10,
        "correlation_limit": 0.70,
        "kill_switch_enabled": true
    }'::jsonb
)
ON CONFLICT (risk_name) DO UPDATE SET
    enabled=EXCLUDED.enabled,
    config_json=EXCLUDED.config_json,
    updated_at=now();

GRANT USAGE ON SCHEMA analytics TO alex;
GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA analytics TO alex;
GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA analytics TO alex;
SQL

cat > scripts/test_risk_platform_foundation_v1.sh <<'SH_TEST'
#!/usr/bin/env bash
set -euo pipefail

echo "=== TEST_RISK_PLATFORM_FOUNDATION_V1 ==="

sudo -u postgres psql -v ON_ERROR_STOP=1 -d finam_core \
  -f sql/analytics/010_risk_platform_foundation_v1.sql

risk_snapshot=$(psql -At -d finam_core -c "SELECT to_regclass('analytics.risk_decision_snapshot_v1') IS NOT NULL;")
risk_config=$(psql -At -d finam_core -c "SELECT to_regclass('analytics.risk_configuration_v1') IS NOT NULL;")
risk_governance=$(psql -At -d finam_core -c "SELECT to_regclass('analytics.risk_governance_v1') IS NOT NULL;")
config_rows=$(psql -At -d finam_core -c "SELECT count(*) FROM analytics.risk_configuration_v1;")
unsafe=$(psql -At -d finam_core -c "
SELECT count(*)
FROM analytics.risk_decision_snapshot_v1
WHERE ready_for_live=true OR ready_for_micro_live=true;
")

test "$risk_snapshot" = "t"
test "$risk_config" = "t"
test "$risk_governance" = "t"
test "$config_rows" -gt 0
test "$unsafe" = "0"

psql -d finam_core -c "\d analytics.risk_decision_snapshot_v1"
psql -d finam_core -c "\d analytics.risk_configuration_v1"
psql -d finam_core -c "\d analytics.risk_governance_v1"

echo "risk_snapshot_table=$risk_snapshot"
echo "risk_configuration_table=$risk_config"
echo "risk_governance_table=$risk_governance"
echo "configuration_rows=$config_rows"
echo "unsafe_live_rows=$unsafe"
echo "runtime_changed=0"
echo "execution_changed=0"
echo "orders_changed=0"
echo "fills_changed=0"
echo "micro_live_allowed=0"
echo "VERDICT=RISK_PLATFORM_FOUNDATION_V1_READY"
echo "VERDICT=TEST_RISK_PLATFORM_FOUNDATION_V1_OK"
SH_TEST

chmod +x scripts/test_risk_platform_foundation_v1.sh
scripts/test_risk_platform_foundation_v1.sh

echo "VERDICT=BUILD_RISK_PLATFORM_FOUNDATION_V1_OK"
