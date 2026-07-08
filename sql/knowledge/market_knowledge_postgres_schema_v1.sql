CREATE SCHEMA IF NOT EXISTS knowledge;

CREATE TABLE IF NOT EXISTS knowledge.market_v1 (
    market_id BIGSERIAL PRIMARY KEY,
    market_code TEXT NOT NULL UNIQUE,
    market_name TEXT NOT NULL,
    description TEXT,
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    source_version TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS knowledge.exchange_v1 (
    exchange_id BIGSERIAL PRIMARY KEY,
    market_id BIGINT REFERENCES knowledge.market_v1(market_id),
    exchange_code TEXT NOT NULL UNIQUE,
    exchange_name TEXT NOT NULL,
    timezone TEXT NOT NULL,
    currency TEXT NOT NULL,
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    source_version TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS knowledge.asset_class_v1 (
    asset_class_id BIGSERIAL PRIMARY KEY,
    asset_class_code TEXT NOT NULL UNIQUE,
    asset_class_name TEXT NOT NULL,
    description TEXT,
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    source_version TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS knowledge.sector_v1 (
    sector_id BIGSERIAL PRIMARY KEY,
    sector_code TEXT NOT NULL UNIQUE,
    sector_name TEXT NOT NULL,
    description TEXT,
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    source_version TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS knowledge.industry_v1 (
    industry_id BIGSERIAL PRIMARY KEY,
    sector_id BIGINT REFERENCES knowledge.sector_v1(sector_id),
    industry_code TEXT NOT NULL UNIQUE,
    industry_name TEXT NOT NULL,
    description TEXT,
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    source_version TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS knowledge.instrument_v1 (
    instrument_id BIGSERIAL PRIMARY KEY,
    symbol TEXT NOT NULL UNIQUE,
    exchange_id BIGINT REFERENCES knowledge.exchange_v1(exchange_id),
    asset_class_id BIGINT REFERENCES knowledge.asset_class_v1(asset_class_id),
    sector_id BIGINT REFERENCES knowledge.sector_v1(sector_id),
    industry_id BIGINT REFERENCES knowledge.industry_v1(industry_id),
    instrument_name TEXT,
    currency TEXT,
    lot_size NUMERIC,
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    source_version TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS knowledge.market_regime_v1 (
    regime_id BIGSERIAL PRIMARY KEY,
    regime_code TEXT NOT NULL UNIQUE,
    regime_name TEXT NOT NULL,
    regime_group TEXT NOT NULL,
    description TEXT,
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    source_version TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS knowledge.market_context_v1 (
    context_id BIGSERIAL PRIMARY KEY,
    symbol TEXT NOT NULL,
    regime_code TEXT NOT NULL,
    context_date DATE NOT NULL,
    timeframe TEXT NOT NULL,
    volatility_state TEXT,
    liquidity_state TEXT,
    volume_state TEXT,
    spread_state TEXT,
    correlation_state TEXT,
    sector_strength_state TEXT,
    session_state TEXT,
    confidence NUMERIC,
    evidence_json JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    source_version TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS knowledge.strategy_context_v1 (
    strategy_context_id BIGSERIAL PRIMARY KEY,
    strategy_code TEXT NOT NULL,
    regime_code TEXT NOT NULL,
    asset_class_code TEXT,
    sector_code TEXT,
    expected_behavior TEXT,
    confidence NUMERIC,
    evidence_json JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    source_version TEXT NOT NULL,
    UNIQUE(strategy_code, regime_code, asset_class_code, sector_code, source_version)
);

CREATE TABLE IF NOT EXISTS knowledge.edge_context_v1 (
    edge_context_id BIGSERIAL PRIMARY KEY,
    symbol TEXT NOT NULL,
    strategy_code TEXT NOT NULL,
    timeframe TEXT NOT NULL,
    regime_code TEXT,
    context_id BIGINT REFERENCES knowledge.market_context_v1(context_id),
    edge_score_v2 NUMERIC,
    context_confidence NUMERIC,
    context_verdict TEXT,
    explanation TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    source_version TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS knowledge.relationship_v1 (
    relationship_id BIGSERIAL PRIMARY KEY,
    source_type TEXT NOT NULL,
    source_code TEXT NOT NULL,
    relation_type TEXT NOT NULL,
    target_type TEXT NOT NULL,
    target_code TEXT NOT NULL,
    weight NUMERIC,
    confidence NUMERIC,
    evidence_json JSONB NOT NULL DEFAULT '{}'::jsonb,
    valid_from DATE,
    valid_to DATE,
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    source_version TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS knowledge.observation_v1 (
    observation_id BIGSERIAL PRIMARY KEY,
    symbol TEXT NOT NULL,
    strategy_code TEXT NOT NULL,
    timeframe TEXT NOT NULL,
    observation_type TEXT NOT NULL,
    observation_value NUMERIC,
    regime_code TEXT,
    context_id BIGINT REFERENCES knowledge.market_context_v1(context_id),
    confirms_edge BOOLEAN NOT NULL DEFAULT FALSE,
    weakens_edge BOOLEAN NOT NULL DEFAULT FALSE,
    rejects_edge BOOLEAN NOT NULL DEFAULT FALSE,
    evidence_json JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    source_version TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS knowledge.recommendation_v1 (
    recommendation_id BIGSERIAL PRIMARY KEY,
    symbol TEXT NOT NULL,
    strategy_code TEXT NOT NULL,
    timeframe TEXT NOT NULL,
    recommendation_code TEXT NOT NULL,
    recommendation_text TEXT,
    reason_code TEXT,
    regime_code TEXT,
    context_id BIGINT REFERENCES knowledge.market_context_v1(context_id),
    confidence NUMERIC,
    execution_allowed INTEGER NOT NULL DEFAULT 0,
    runtime_allowed INTEGER NOT NULL DEFAULT 0,
    micro_live_allowed INTEGER NOT NULL DEFAULT 0,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    source_version TEXT NOT NULL,
    CHECK (execution_allowed = 0),
    CHECK (runtime_allowed = 0),
    CHECK (micro_live_allowed = 0)
);

CREATE INDEX IF NOT EXISTS idx_market_context_symbol_date
ON knowledge.market_context_v1(symbol, context_date, timeframe);

CREATE INDEX IF NOT EXISTS idx_edge_context_symbol_strategy
ON knowledge.edge_context_v1(symbol, strategy_code, timeframe);

CREATE INDEX IF NOT EXISTS idx_relationship_source
ON knowledge.relationship_v1(source_type, source_code, relation_type);

CREATE INDEX IF NOT EXISTS idx_relationship_target
ON knowledge.relationship_v1(target_type, target_code);

CREATE INDEX IF NOT EXISTS idx_observation_symbol_strategy
ON knowledge.observation_v1(symbol, strategy_code, timeframe);

CREATE INDEX IF NOT EXISTS idx_recommendation_symbol_strategy
ON knowledge.recommendation_v1(symbol, strategy_code, timeframe);
