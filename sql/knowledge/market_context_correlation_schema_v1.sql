CREATE TABLE IF NOT EXISTS knowledge.correlation_rule_v1 (
    rule_id BIGSERIAL PRIMARY KEY,
    rule_code TEXT NOT NULL UNIQUE,
    relation_type TEXT NOT NULL,
    timeframe TEXT NOT NULL,
    lookback_bars INTEGER NOT NULL CHECK (lookback_bars > 1),
    min_observations INTEGER NOT NULL CHECK (min_observations > 1),
    min_abs_correlation NUMERIC NOT NULL CHECK (min_abs_correlation >= 0 AND min_abs_correlation <= 1),
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    source_version TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS knowledge.correlation_universe_v1 (
    universe_id BIGSERIAL PRIMARY KEY,
    source_symbol TEXT NOT NULL,
    target_symbol TEXT NOT NULL,
    timeframe TEXT NOT NULL,
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    source_version TEXT NOT NULL,
    UNIQUE(source_symbol, target_symbol, timeframe, source_version),
    CHECK (source_symbol <> target_symbol)
);

CREATE INDEX IF NOT EXISTS idx_correlation_rule_active_v1
ON knowledge.correlation_rule_v1(is_active, timeframe);

CREATE INDEX IF NOT EXISTS idx_correlation_universe_source_v1
ON knowledge.correlation_universe_v1(source_symbol, timeframe, is_active);

CREATE INDEX IF NOT EXISTS idx_correlation_universe_target_v1
ON knowledge.correlation_universe_v1(target_symbol, timeframe, is_active);
