CREATE SCHEMA IF NOT EXISTS marketcore;

CREATE TABLE IF NOT EXISTS marketcore.instrument_reference_v1 (
    symbol TEXT PRIMARY KEY,
    display_name TEXT NOT NULL DEFAULT '',
    short_name TEXT NOT NULL DEFAULT '',
    asset_class TEXT NOT NULL DEFAULT '',
    exchange TEXT NOT NULL DEFAULT '',
    board TEXT NOT NULL DEFAULT '',
    currency TEXT NOT NULL DEFAULT '',
    lot_size NUMERIC(20,6),
    min_price_step NUMERIC(20,8),
    price_scale INTEGER,
    tick_value NUMERIC(20,8),
    contract_size NUMERIC(20,8),
    expiration_date DATE,
    underlying_symbol TEXT NOT NULL DEFAULT '',
    finam_security_code TEXT NOT NULL DEFAULT '',
    finam_market TEXT NOT NULL DEFAULT '',
    moex_secid TEXT NOT NULL DEFAULT '',
    isin TEXT NOT NULL DEFAULT '',
    figi TEXT NOT NULL DEFAULT '',
    is_active BOOLEAN NOT NULL DEFAULT true,
    is_tradable BOOLEAN NOT NULL DEFAULT true,
    first_seen TIMESTAMPTZ NOT NULL DEFAULT now(),
    last_seen TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    source TEXT NOT NULL DEFAULT 'MARKET_SNAPSHOT',
    source_version TEXT NOT NULL DEFAULT 'INSTRUMENT_REFERENCE_V1',
    build_id TEXT NOT NULL DEFAULT 'manual'
);

CREATE INDEX IF NOT EXISTS ix_instrument_reference_v1_asset_class
ON marketcore.instrument_reference_v1(asset_class);

CREATE INDEX IF NOT EXISTS ix_instrument_reference_v1_exchange
ON marketcore.instrument_reference_v1(exchange);

CREATE INDEX IF NOT EXISTS ix_instrument_reference_v1_active
ON marketcore.instrument_reference_v1(is_active);

GRANT USAGE ON SCHEMA marketcore TO alex;
GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA marketcore TO alex;
