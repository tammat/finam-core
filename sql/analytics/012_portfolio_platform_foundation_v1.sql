CREATE TABLE IF NOT EXISTS analytics.portfolio_position_snapshot_v1 (
    id BIGSERIAL PRIMARY KEY,

    symbol TEXT NOT NULL,
    asset_class TEXT NOT NULL DEFAULT '',
    quantity NUMERIC(20,8) NOT NULL DEFAULT 0,
    avg_price NUMERIC(20,8) NOT NULL DEFAULT 0,
    last_price NUMERIC(20,8) NOT NULL DEFAULT 0,

    market_value NUMERIC(20,8) NOT NULL DEFAULT 0,
    unrealized_pnl NUMERIC(20,8) NOT NULL DEFAULT 0,
    realized_pnl NUMERIC(20,8) NOT NULL DEFAULT 0,
    exposure NUMERIC(20,8) NOT NULL DEFAULT 0,

    position_status TEXT NOT NULL DEFAULT 'EMPTY',

    source_version TEXT NOT NULL DEFAULT 'PORTFOLIO_PLATFORM_FOUNDATION_V1',
    build_id TEXT NOT NULL DEFAULT 'manual',
    refreshed_at TIMESTAMPTZ NOT NULL DEFAULT now(),

    UNIQUE(symbol)
);

CREATE TABLE IF NOT EXISTS analytics.portfolio_equity_snapshot_v1 (
    portfolio_scope TEXT PRIMARY KEY DEFAULT 'GLOBAL',

    cash NUMERIC(20,8) NOT NULL DEFAULT 0,
    positions_value NUMERIC(20,8) NOT NULL DEFAULT 0,
    equity NUMERIC(20,8) NOT NULL DEFAULT 0,

    realized_pnl NUMERIC(20,8) NOT NULL DEFAULT 0,
    unrealized_pnl NUMERIC(20,8) NOT NULL DEFAULT 0,
    total_pnl NUMERIC(20,8) NOT NULL DEFAULT 0,

    gross_exposure NUMERIC(20,8) NOT NULL DEFAULT 0,
    net_exposure NUMERIC(20,8) NOT NULL DEFAULT 0,

    source_version TEXT NOT NULL DEFAULT 'PORTFOLIO_PLATFORM_FOUNDATION_V1',
    build_id TEXT NOT NULL DEFAULT 'manual',
    refreshed_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS analytics.portfolio_configuration_v1 (
    portfolio_name TEXT PRIMARY KEY,
    enabled BOOLEAN NOT NULL DEFAULT true,
    config_json JSONB NOT NULL DEFAULT '{}'::jsonb,
    source_version TEXT NOT NULL DEFAULT 'PORTFOLIO_PLATFORM_FOUNDATION_V1',
    build_id TEXT NOT NULL DEFAULT 'manual',
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS analytics.portfolio_governance_v1 (
    governance_scope TEXT PRIMARY KEY,

    builder_status TEXT NOT NULL DEFAULT 'UNKNOWN',
    position_status TEXT NOT NULL DEFAULT 'UNKNOWN',
    equity_status TEXT NOT NULL DEFAULT 'UNKNOWN',
    api_status TEXT NOT NULL DEFAULT 'UNKNOWN',
    ui_status TEXT NOT NULL DEFAULT 'UNKNOWN',

    governance_score NUMERIC(10,4) NOT NULL DEFAULT 0,
    readiness_code TEXT NOT NULL DEFAULT 'NOT_READY',
    recommendation_code TEXT NOT NULL DEFAULT 'WAIT_PORTFOLIO_FOUNDATION',

    source_version TEXT NOT NULL DEFAULT 'PORTFOLIO_PLATFORM_FOUNDATION_V1',
    build_id TEXT NOT NULL DEFAULT 'manual',
    refreshed_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

INSERT INTO analytics.portfolio_configuration_v1 (
    portfolio_name,
    enabled,
    config_json
)
VALUES (
    'DEFAULT',
    true,
    '{
        "base_currency": "RUB",
        "initial_cash": 0,
        "include_paper": true,
        "include_shadow": false,
        "include_micro_live": false,
        "include_live": false
    }'::jsonb
)
ON CONFLICT (portfolio_name) DO UPDATE SET
    enabled=EXCLUDED.enabled,
    config_json=EXCLUDED.config_json,
    updated_at=now();

INSERT INTO analytics.portfolio_equity_snapshot_v1 (
    portfolio_scope,
    cash,
    positions_value,
    equity,
    realized_pnl,
    unrealized_pnl,
    total_pnl,
    gross_exposure,
    net_exposure,
    source_version
)
VALUES (
    'GLOBAL',
    0,0,0,0,0,0,0,0,
    'PORTFOLIO_PLATFORM_FOUNDATION_V1'
)
ON CONFLICT (portfolio_scope) DO NOTHING;

GRANT USAGE ON SCHEMA analytics TO alex;
GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA analytics TO alex;
GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA analytics TO alex;
