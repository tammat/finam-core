CREATE TABLE IF NOT EXISTS instrument_specs (
    id BIGSERIAL PRIMARY KEY,
    symbol TEXT NOT NULL UNIQUE,
    base_symbol TEXT NOT NULL,
    asset_class TEXT NOT NULL,
    exchange TEXT,
    board TEXT,
    min_price_step DOUBLE PRECISION,
    step_value DOUBLE PRECISION,
    lot_size DOUBLE PRECISION DEFAULT 1,
    currency TEXT DEFAULT 'RUB',
    initial_margin DOUBLE PRECISION,
    maintenance_margin DOUBLE PRECISION,
    broker_fee DOUBLE PRECISION DEFAULT 0,
    exchange_fee DOUBLE PRECISION DEFAULT 0,
    clearing_fee DOUBLE PRECISION DEFAULT 0,
    tax_rate DOUBLE PRECISION DEFAULT 0.13,
    source TEXT NOT NULL DEFAULT 'manual',
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    raw_json JSONB NOT NULL DEFAULT '{}'::jsonb
);

CREATE INDEX IF NOT EXISTS idx_instrument_specs_base_symbol
    ON instrument_specs (base_symbol);

CREATE INDEX IF NOT EXISTS idx_instrument_specs_asset_class
    ON instrument_specs (asset_class);
