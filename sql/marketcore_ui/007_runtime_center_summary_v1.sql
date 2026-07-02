BEGIN;

CREATE TABLE IF NOT EXISTS marketcore_ui.runtime_center_summary_v1 (
    id SMALLINT PRIMARY KEY,
    runtime_status TEXT NOT NULL DEFAULT 'OFF',
    paper_status TEXT NOT NULL DEFAULT 'READY',
    production_status TEXT NOT NULL DEFAULT 'OFF',
    risk_status TEXT NOT NULL DEFAULT 'SAFE',
    active_symbols INTEGER NOT NULL DEFAULT 0,
    active_edges INTEGER NOT NULL DEFAULT 0,
    active_positions INTEGER NOT NULL DEFAULT 0,
    signals_today INTEGER NOT NULL DEFAULT 0,
    trades_today INTEGER NOT NULL DEFAULT 0,
    pnl_today NUMERIC(20,2) NOT NULL DEFAULT 0,
    next_action TEXT NOT NULL DEFAULT 'PAPER_CENTER_REVIEW',
    refreshed_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    source_version TEXT NOT NULL DEFAULT 'MARKETCORE_RUNTIME_CENTER_READ_MODEL_V1',
    build_id TEXT NOT NULL DEFAULT 'migration_default'
);

INSERT INTO marketcore_ui.runtime_center_summary_v1 (id)
VALUES (1)
ON CONFLICT (id) DO NOTHING;

GRANT USAGE ON SCHEMA marketcore_ui TO alex;
GRANT SELECT ON marketcore_ui.runtime_center_summary_v1 TO alex;

COMMIT;
