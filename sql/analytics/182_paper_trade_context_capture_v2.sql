CREATE TABLE IF NOT EXISTS analytics.paper_trade_context_capture_state_v2 (
    state_id BOOLEAN PRIMARY KEY DEFAULT true CHECK (state_id),
    schema_version TEXT NOT NULL DEFAULT 'V2',
    activated_at TIMESTAMPTZ NOT NULL DEFAULT clock_timestamp(),
    active BOOLEAN NOT NULL DEFAULT true,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT clock_timestamp()
);

INSERT INTO analytics.paper_trade_context_capture_state_v2(state_id,schema_version)
VALUES (true,'V2')
ON CONFLICT(state_id) DO NOTHING;

GRANT SELECT ON analytics.paper_trade_context_capture_state_v2 TO alex;
