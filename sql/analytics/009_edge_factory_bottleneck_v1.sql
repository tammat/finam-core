CREATE TABLE IF NOT EXISTS analytics.edge_factory_bottleneck_v1
(
    id                  BIGSERIAL PRIMARY KEY,
    snapshot_ts         timestamptz NOT NULL DEFAULT now(),

    pipeline_stage      text NOT NULL,

    source_count        bigint NOT NULL,
    target_count        bigint NOT NULL,

    conversion_pct      numeric(12,6) NOT NULL,

    severity            text NOT NULL,

    root_cause_code     text NOT NULL,

    recommendation_code text NOT NULL,

    expected_gain_pct   numeric(12,6),

    source_version      text NOT NULL,

    created_at          timestamptz NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS
idx_edge_factory_bottleneck_snapshot
ON analytics.edge_factory_bottleneck_v1(snapshot_ts DESC);
