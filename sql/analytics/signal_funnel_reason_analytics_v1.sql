CREATE TABLE IF NOT EXISTS analytics.signal_funnel_reason_snapshot_v1 (
    signal_funnel_reason_snapshot_id BIGSERIAL PRIMARY KEY,
    source_version TEXT NOT NULL,
    evidence_json JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS analytics.signal_funnel_reason_v1 (
    signal_funnel_reason_id BIGSERIAL PRIMARY KEY,
    signal_funnel_reason_snapshot_id BIGINT NOT NULL
        REFERENCES analytics.signal_funnel_reason_snapshot_v1(signal_funnel_reason_snapshot_id)
        ON DELETE CASCADE,
    source_schema TEXT NOT NULL,
    source_table TEXT NOT NULL,
    reason_column TEXT NOT NULL,
    reason_value TEXT NOT NULL,
    rows_total NUMERIC NOT NULL DEFAULT 0,
    reason_group TEXT NOT NULL,
    evidence_json JSONB NOT NULL DEFAULT '{}'::jsonb,
    source_version TEXT NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_signal_funnel_reason_v1
ON analytics.signal_funnel_reason_v1(signal_funnel_reason_snapshot_id, rows_total DESC);
