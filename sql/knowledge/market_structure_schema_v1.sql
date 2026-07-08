CREATE TABLE IF NOT EXISTS knowledge.market_structure_type_v1 (
    structure_type_code TEXT PRIMARY KEY,
    structure_type_name TEXT NOT NULL,
    enabled BOOLEAN NOT NULL DEFAULT TRUE,
    source_version TEXT NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS knowledge.market_structure_v1 (
    structure_id BIGSERIAL PRIMARY KEY,
    symbol TEXT NOT NULL,
    timeframe TEXT NOT NULL,
    structure_type_code TEXT NOT NULL
        REFERENCES knowledge.market_structure_type_v1(structure_type_code),

    level_price NUMERIC NOT NULL,
    level_strength NUMERIC,
    lookback_bars INTEGER NOT NULL CHECK (lookback_bars > 0),

    detected_at TIMESTAMPTZ NOT NULL,
    valid_from TIMESTAMPTZ NOT NULL DEFAULT now(),
    valid_to TIMESTAMPTZ,

    evidence_json JSONB NOT NULL DEFAULT '{}'::jsonb,
    source_version TEXT NOT NULL,

    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_market_structure_symbol_tf_v1
ON knowledge.market_structure_v1(symbol, timeframe, structure_type_code);

CREATE INDEX IF NOT EXISTS idx_market_structure_valid_v1
ON knowledge.market_structure_v1(symbol, timeframe, valid_to);
