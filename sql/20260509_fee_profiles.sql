CREATE TABLE IF NOT EXISTS fee_profiles (
    id BIGSERIAL PRIMARY KEY,
    profile_name TEXT NOT NULL,
    asset_class TEXT NOT NULL,
    symbol_prefix TEXT,
    broker_fee_per_contract DOUBLE PRECISION DEFAULT 0,
    exchange_fee_per_contract DOUBLE PRECISION DEFAULT 0,
    clearing_fee_per_contract DOUBLE PRECISION DEFAULT 0,
    broker_fee_pct DOUBLE PRECISION DEFAULT 0,
    exchange_fee_pct DOUBLE PRECISION DEFAULT 0,
    min_fee DOUBLE PRECISION DEFAULT 0,
    currency TEXT DEFAULT 'RUB',
    source TEXT DEFAULT 'manual',
    active BOOLEAN NOT NULL DEFAULT TRUE,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    raw_json JSONB NOT NULL DEFAULT '{}'::jsonb
);

CREATE INDEX IF NOT EXISTS idx_fee_profiles_lookup
ON fee_profiles (asset_class, symbol_prefix, active);
