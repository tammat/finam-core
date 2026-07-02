BEGIN;

CREATE TABLE IF NOT EXISTS marketcore_ui.capital_manager_summary_v1 (
    id SMALLINT PRIMARY KEY,
    planned_capital NUMERIC(20,2) NOT NULL DEFAULT 0,
    working_capital NUMERIC(20,2) NOT NULL DEFAULT 0,
    available_capital NUMERIC(20,2) NOT NULL DEFAULT 0,
    exposure_pct NUMERIC(10,2) NOT NULL DEFAULT 0,
    deployment_limit_pct NUMERIC(10,2) NOT NULL DEFAULT 0,
    risk_mode TEXT NOT NULL DEFAULT 'READ_ONLY',
    manager_status TEXT NOT NULL DEFAULT 'READY',
    next_action TEXT NOT NULL DEFAULT 'PAPER_RUNTIME_REVIEW',
    refreshed_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    source_version TEXT NOT NULL DEFAULT 'MARKETCORE_CAPITAL_MANAGER_V1',
    build_id TEXT NOT NULL DEFAULT 'manual'
);

INSERT INTO marketcore_ui.capital_manager_summary_v1 (
    id, planned_capital, working_capital, available_capital,
    exposure_pct, deployment_limit_pct, risk_mode, manager_status,
    next_action, refreshed_at, source_version, build_id
)
VALUES (
    1, 500000, 0, 500000,
    0, 0, 'READ_ONLY', 'READY',
    'PAPER_RUNTIME_REVIEW', now(),
    'MARKETCORE_CAPITAL_MANAGER_V1', 'migration_default'
)
ON CONFLICT (id) DO NOTHING;

GRANT USAGE ON SCHEMA marketcore_ui TO alex;
GRANT SELECT ON marketcore_ui.capital_manager_summary_v1 TO alex;

COMMIT;
