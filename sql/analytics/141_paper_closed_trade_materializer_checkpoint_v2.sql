BEGIN;

CREATE TABLE IF NOT EXISTS analytics.paper_closed_trade_materializer_checkpoint_v2 (
    symbol text PRIMARY KEY,
    fill_count bigint NOT NULL CHECK (fill_count >= 0),
    max_fill_ts timestamptz,
    last_success_at timestamptz NOT NULL,
    updated_at timestamptz NOT NULL DEFAULT clock_timestamp()
);

GRANT SELECT, INSERT, UPDATE, DELETE
ON analytics.paper_closed_trade_materializer_checkpoint_v2 TO finam;
GRANT SELECT ON analytics.paper_closed_trade_materializer_checkpoint_v2 TO alex;

COMMIT;
