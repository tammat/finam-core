CREATE TABLE IF NOT EXISTS analytics.profit_factory_reconciliation_run_v1 (
    run_id UUID PRIMARY KEY,
    engine_version TEXT NOT NULL,
    mode TEXT NOT NULL,
    status TEXT NOT NULL,
    started_at TIMESTAMPTZ NOT NULL,
    finished_at TIMESTAMPTZ,
    source_rows INTEGER NOT NULL DEFAULT 0,
    created_rows INTEGER NOT NULL DEFAULT 0,
    updated_rows INTEGER NOT NULL DEFAULT 0,
    conflict_rows INTEGER NOT NULL DEFAULT 0,
    stale_rows INTEGER NOT NULL DEFAULT 0,
    skipped_rows INTEGER NOT NULL DEFAULT 0,
    error_text TEXT,
    CONSTRAINT ck_profit_factory_reconciliation_mode_v1
        CHECK (mode IN ('DRY_RUN', 'APPLY')),
    CONSTRAINT ck_profit_factory_reconciliation_status_v1
        CHECK (status IN ('RUNNING', 'COMPLETED', 'FAILED'))
);

CREATE INDEX IF NOT EXISTS ix_profit_factory_reconciliation_run_started_v1
ON analytics.profit_factory_reconciliation_run_v1(started_at DESC);

GRANT SELECT, INSERT, UPDATE ON analytics.profit_factory_reconciliation_run_v1 TO alex;
