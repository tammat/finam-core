CREATE TABLE IF NOT EXISTS market_sync_state (
    symbol TEXT NOT NULL,
    timeframe TEXT NOT NULL,
    last_synced_ts TIMESTAMPTZ,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    PRIMARY KEY (symbol, timeframe)
);

CREATE INDEX IF NOT EXISTS ix_market_sync_state_updated
    ON market_sync_state (updated_at DESC);