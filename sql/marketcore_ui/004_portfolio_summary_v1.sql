BEGIN;

CREATE TABLE IF NOT EXISTS marketcore_ui.portfolio_summary_v1 (
    id SMALLINT PRIMARY KEY,
    planned_capital NUMERIC(20,2) NOT NULL DEFAULT 0,
    working_capital NUMERIC(20,2) NOT NULL DEFAULT 0,
    available_capital NUMERIC(20,2) NOT NULL DEFAULT 0,
    today_pnl NUMERIC(20,2) NOT NULL DEFAULT 0,
    open_positions INTEGER NOT NULL DEFAULT 0,
    paper_positions INTEGER NOT NULL DEFAULT 0,
    production_positions INTEGER NOT NULL DEFAULT 0,
    exposure_pct NUMERIC(10,2) NOT NULL DEFAULT 0,
    portfolio_status TEXT NOT NULL DEFAULT 'READY',
    next_action TEXT NOT NULL DEFAULT 'MARKETCORE_INTRADAY_WORKSPACE_V1',
    refreshed_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    source_version TEXT NOT NULL DEFAULT 'MARKETCORE_PORTFOLIO_READ_MODEL_V1',
    build_id TEXT NOT NULL DEFAULT 'manual'
);

INSERT INTO marketcore_ui.portfolio_summary_v1 (
    id, planned_capital, working_capital, available_capital, today_pnl,
    open_positions, paper_positions, production_positions, exposure_pct,
    portfolio_status, next_action, refreshed_at, source_version, build_id
)
VALUES (
    1, 500000, 0, 500000, 0,
    0, 0, 0, 0,
    'READY', 'MARKETCORE_INTRADAY_WORKSPACE_V1',
    now(), 'MARKETCORE_PORTFOLIO_READ_MODEL_V1', 'migration_default'
)
ON CONFLICT (id) DO NOTHING;

GRANT USAGE ON SCHEMA marketcore_ui TO alex;
GRANT SELECT ON marketcore_ui.portfolio_summary_v1 TO alex;

COMMIT;
