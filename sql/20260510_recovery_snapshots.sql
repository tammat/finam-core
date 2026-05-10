CREATE TABLE IF NOT EXISTS recovery_snapshots (
    id BIGSERIAL PRIMARY KEY,
    snapshot_id TEXT NOT NULL UNIQUE,
    aggregate_type TEXT NOT NULL,
    aggregate_id TEXT NOT NULL,
    event_offset BIGINT NOT NULL DEFAULT 0,
    cash_delta DOUBLE PRECISION NOT NULL DEFAULT 0,
    positions JSONB NOT NULL DEFAULT '{}'::jsonb,
    realized_pnl DOUBLE PRECISION NOT NULL DEFAULT 0,
    source TEXT NOT NULL DEFAULT 'recovery_snapshot_service',
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_recovery_snapshots_aggregate
ON recovery_snapshots(aggregate_type, aggregate_id);

CREATE INDEX IF NOT EXISTS idx_recovery_snapshots_created_at
ON recovery_snapshots(created_at);
