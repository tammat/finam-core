CREATE TABLE IF NOT EXISTS margin_requirements (
    id BIGSERIAL PRIMARY KEY,
    symbol TEXT NOT NULL UNIQUE,
    base_symbol TEXT NOT NULL,
    asset_class TEXT NOT NULL,
    initial_margin DOUBLE PRECISION NOT NULL DEFAULT 0,
    maintenance_margin DOUBLE PRECISION NOT NULL DEFAULT 0,
    currency TEXT NOT NULL DEFAULT 'RUB',
    source TEXT NOT NULL DEFAULT 'manual',
    active BOOLEAN NOT NULL DEFAULT TRUE,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    raw_json JSONB NOT NULL DEFAULT '{}'::jsonb
);

CREATE INDEX IF NOT EXISTS idx_margin_requirements_base_symbol
ON margin_requirements (base_symbol);

CREATE INDEX IF NOT EXISTS idx_margin_requirements_asset_class
ON margin_requirements (asset_class, active);
