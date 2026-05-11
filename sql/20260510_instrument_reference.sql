CREATE TABLE IF NOT EXISTS instrument_reference (
    symbol TEXT PRIMARY KEY,
    short_name TEXT,
    display_name TEXT,
    board TEXT,
    market TEXT,
    asset_class TEXT,
    sector TEXT,
    logo_url TEXT,
    source TEXT NOT NULL DEFAULT 'finam',
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_instrument_reference_market
ON instrument_reference(market);

CREATE INDEX IF NOT EXISTS idx_instrument_reference_asset_class
ON instrument_reference(asset_class);
