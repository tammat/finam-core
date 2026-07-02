BEGIN;

CREATE TABLE IF NOT EXISTS marketcore_ui.daily_center_summary_v1 (
    id SMALLINT PRIMARY KEY,
    day_status TEXT NOT NULL DEFAULT 'READY',
    capital_status TEXT NOT NULL DEFAULT 'READY',
    research_status TEXT NOT NULL DEFAULT 'READY',
    risk_status TEXT NOT NULL DEFAULT 'SAFE',
    runtime_status TEXT NOT NULL DEFAULT 'OFF',
    next_action TEXT NOT NULL DEFAULT 'PAPER_RUNTIME_REVIEW',
    decision_hint TEXT NOT NULL DEFAULT 'Открыть Capital Manager и проверить готовность Paper Runtime',
    refreshed_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    source_version TEXT NOT NULL DEFAULT 'MARKETCORE_DAILY_CENTER_V1',
    build_id TEXT NOT NULL DEFAULT 'manual'
);

INSERT INTO marketcore_ui.daily_center_summary_v1 (
    id, day_status, capital_status, research_status, risk_status,
    runtime_status, next_action, decision_hint, refreshed_at, source_version, build_id
)
VALUES (
    1, 'READY', 'READY', 'READY', 'SAFE',
    'OFF', 'PAPER_RUNTIME_REVIEW',
    'Открыть Capital Manager и проверить готовность Paper Runtime',
    now(), 'MARKETCORE_DAILY_CENTER_V1', 'migration_default'
)
ON CONFLICT (id) DO NOTHING;

GRANT USAGE ON SCHEMA marketcore_ui TO alex;
GRANT SELECT ON marketcore_ui.daily_center_summary_v1 TO alex;

COMMIT;
