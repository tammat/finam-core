CREATE SCHEMA IF NOT EXISTS analytics;

CREATE TABLE IF NOT EXISTS analytics.analytics_snapshot_v1 (
    analytics_snapshot_id BIGSERIAL PRIMARY KEY,
    snapshot_type TEXT NOT NULL,
    source_version TEXT NOT NULL,
    evidence_json JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS analytics.paper_execution_summary_v1 (
    summary_id BIGSERIAL PRIMARY KEY,
    analytics_snapshot_id BIGINT NOT NULL
        REFERENCES analytics.analytics_snapshot_v1(analytics_snapshot_id)
        ON DELETE CASCADE,

    trades_total INTEGER NOT NULL DEFAULT 0,
    wins_total INTEGER NOT NULL DEFAULT 0,
    losses_total INTEGER NOT NULL DEFAULT 0,
    flat_total INTEGER NOT NULL DEFAULT 0,

    gross_profit NUMERIC NOT NULL DEFAULT 0,
    gross_loss NUMERIC NOT NULL DEFAULT 0,
    net_pnl_points NUMERIC NOT NULL DEFAULT 0,

    profit_factor NUMERIC,
    expectancy_r NUMERIC,
    win_rate NUMERIC,
    avg_r_multiple NUMERIC,
    avg_mae_points NUMERIC,
    avg_mfe_points NUMERIC,
    avg_bars_held NUMERIC,

    source_version TEXT NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS analytics.paper_execution_profile_scorecard_v1 (
    profile_scorecard_id BIGSERIAL PRIMARY KEY,
    analytics_snapshot_id BIGINT NOT NULL
        REFERENCES analytics.analytics_snapshot_v1(analytics_snapshot_id)
        ON DELETE CASCADE,

    profile_code TEXT NOT NULL,

    trades_total INTEGER NOT NULL DEFAULT 0,
    wins_total INTEGER NOT NULL DEFAULT 0,
    losses_total INTEGER NOT NULL DEFAULT 0,
    flat_total INTEGER NOT NULL DEFAULT 0,

    gross_profit NUMERIC NOT NULL DEFAULT 0,
    gross_loss NUMERIC NOT NULL DEFAULT 0,
    net_pnl_points NUMERIC NOT NULL DEFAULT 0,

    profit_factor NUMERIC,
    expectancy_r NUMERIC,
    win_rate NUMERIC,
    avg_r_multiple NUMERIC,
    avg_mae_points NUMERIC,
    avg_mfe_points NUMERIC,
    avg_bars_held NUMERIC,

    sample_status TEXT NOT NULL DEFAULT 'RESEARCH',
    source_version TEXT NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS analytics.paper_execution_source_scorecard_v1 (
    source_scorecard_id BIGSERIAL PRIMARY KEY,
    analytics_snapshot_id BIGINT NOT NULL
        REFERENCES analytics.analytics_snapshot_v1(analytics_snapshot_id)
        ON DELETE CASCADE,

    entry_source TEXT NOT NULL,
    stop_source TEXT NOT NULL,
    target_source TEXT NOT NULL,

    trades_total INTEGER NOT NULL DEFAULT 0,
    wins_total INTEGER NOT NULL DEFAULT 0,
    losses_total INTEGER NOT NULL DEFAULT 0,
    flat_total INTEGER NOT NULL DEFAULT 0,

    gross_profit NUMERIC NOT NULL DEFAULT 0,
    gross_loss NUMERIC NOT NULL DEFAULT 0,
    net_pnl_points NUMERIC NOT NULL DEFAULT 0,

    profit_factor NUMERIC,
    expectancy_r NUMERIC,
    win_rate NUMERIC,
    avg_r_multiple NUMERIC,
    avg_mae_points NUMERIC,
    avg_mfe_points NUMERIC,
    avg_bars_held NUMERIC,

    sample_status TEXT NOT NULL DEFAULT 'RESEARCH',
    source_version TEXT NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS analytics.paper_execution_regime_scorecard_v1 (
    regime_scorecard_id BIGSERIAL PRIMARY KEY,
    analytics_snapshot_id BIGINT NOT NULL
        REFERENCES analytics.analytics_snapshot_v1(analytics_snapshot_id)
        ON DELETE CASCADE,

    regime_code TEXT NOT NULL,

    trades_total INTEGER NOT NULL DEFAULT 0,
    wins_total INTEGER NOT NULL DEFAULT 0,
    losses_total INTEGER NOT NULL DEFAULT 0,
    flat_total INTEGER NOT NULL DEFAULT 0,

    gross_profit NUMERIC NOT NULL DEFAULT 0,
    gross_loss NUMERIC NOT NULL DEFAULT 0,
    net_pnl_points NUMERIC NOT NULL DEFAULT 0,

    profit_factor NUMERIC,
    expectancy_r NUMERIC,
    win_rate NUMERIC,
    avg_r_multiple NUMERIC,
    avg_mae_points NUMERIC,
    avg_mfe_points NUMERIC,
    avg_bars_held NUMERIC,

    sample_status TEXT NOT NULL DEFAULT 'RESEARCH',
    source_version TEXT NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_analytics_snapshot_type_v1
ON analytics.analytics_snapshot_v1(snapshot_type, created_at DESC);

CREATE INDEX IF NOT EXISTS idx_paper_execution_summary_snapshot_v1
ON analytics.paper_execution_summary_v1(analytics_snapshot_id);

CREATE INDEX IF NOT EXISTS idx_paper_execution_profile_scorecard_snapshot_v1
ON analytics.paper_execution_profile_scorecard_v1(analytics_snapshot_id);

CREATE INDEX IF NOT EXISTS idx_paper_execution_source_scorecard_snapshot_v1
ON analytics.paper_execution_source_scorecard_v1(analytics_snapshot_id);

CREATE INDEX IF NOT EXISTS idx_paper_execution_regime_scorecard_snapshot_v1
ON analytics.paper_execution_regime_scorecard_v1(analytics_snapshot_id);
