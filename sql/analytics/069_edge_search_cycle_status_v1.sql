BEGIN;
CREATE TABLE IF NOT EXISTS analytics.edge_search_cycle_status_v1 (
    cycle_id UUID PRIMARY KEY,
    status_code TEXT NOT NULL CHECK (status_code IN (
        'RUNNING','PASS_FOUND','NO_PASS','NO_CURRENT_MARKETS','FAILED'
    )),
    current_step TEXT NOT NULL,
    progress_pct INTEGER NOT NULL CHECK (progress_pct BETWEEN 0 AND 100),
    freshness_minutes INTEGER NOT NULL CHECK (freshness_minutes > 0),
    markets_evaluated INTEGER NOT NULL DEFAULT 0,
    combinations_evaluated INTEGER NOT NULL DEFAULT 0,
    oos_pass INTEGER NOT NULL DEFAULT 0,
    reason_code TEXT NOT NULL,
    started_at TIMESTAMPTZ NOT NULL DEFAULT clock_timestamp(),
    finished_at TIMESTAMPTZ,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT clock_timestamp()
);
GRANT SELECT,INSERT,UPDATE ON analytics.edge_search_cycle_status_v1 TO alex;
COMMIT;
