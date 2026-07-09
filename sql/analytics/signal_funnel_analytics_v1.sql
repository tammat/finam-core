CREATE TABLE IF NOT EXISTS analytics.signal_funnel_snapshot_v1 (
    signal_funnel_snapshot_id BIGSERIAL PRIMARY KEY,
    source_version TEXT NOT NULL,
    evidence_json JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS analytics.signal_funnel_stage_v1 (
    signal_funnel_stage_id BIGSERIAL PRIMARY KEY,
    signal_funnel_snapshot_id BIGINT NOT NULL
        REFERENCES analytics.signal_funnel_snapshot_v1(signal_funnel_snapshot_id)
        ON DELETE CASCADE,
    stage_order INTEGER NOT NULL,
    stage_code TEXT NOT NULL,
    stage_name TEXT NOT NULL,
    stage_count NUMERIC NOT NULL DEFAULT 0,
    previous_stage_count NUMERIC,
    pass_rate_pct NUMERIC,
    stage_status TEXT NOT NULL,
    evidence_json JSONB NOT NULL DEFAULT '{}'::jsonb,
    source_version TEXT NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_signal_funnel_stage_v1
ON analytics.signal_funnel_stage_v1(signal_funnel_snapshot_id, stage_order);
