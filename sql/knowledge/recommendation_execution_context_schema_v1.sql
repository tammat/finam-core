CREATE TABLE IF NOT EXISTS knowledge.recommendation_direction_v1 (
    direction_code TEXT PRIMARY KEY,
    direction_name TEXT NOT NULL,
    enabled BOOLEAN NOT NULL DEFAULT TRUE,
    source_version TEXT NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS knowledge.recommendation_execution_context_v1 (
    execution_context_id BIGSERIAL PRIMARY KEY,

    recommendation_id BIGINT NOT NULL
        REFERENCES knowledge.recommendation_result_v1(recommendation_id)
        ON DELETE CASCADE,

    direction_code TEXT NOT NULL
        REFERENCES knowledge.recommendation_direction_v1(direction_code),

    entry_price NUMERIC NOT NULL,
    invalidation_price NUMERIC NOT NULL,
    target_price NUMERIC NOT NULL,

    horizon_bars INTEGER NOT NULL CHECK (horizon_bars > 0),
    risk_unit NUMERIC NOT NULL CHECK (risk_unit > 0),

    source_context_id BIGINT NOT NULL
        REFERENCES knowledge.market_context_v1(context_id),

    source_edge_context_id BIGINT NOT NULL
        REFERENCES knowledge.edge_context_v1(edge_context_id),

    execution_allowed INTEGER NOT NULL DEFAULT 0,
    runtime_allowed INTEGER NOT NULL DEFAULT 0,
    micro_live_allowed INTEGER NOT NULL DEFAULT 0,

    evidence_json JSONB NOT NULL DEFAULT '{}'::jsonb,
    source_version TEXT NOT NULL,

    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),

    UNIQUE(recommendation_id, source_version)
);

CREATE INDEX IF NOT EXISTS idx_recommendation_execution_context_symbol_v1
ON knowledge.recommendation_execution_context_v1(recommendation_id, source_version);

CREATE INDEX IF NOT EXISTS idx_recommendation_execution_context_safety_v1
ON knowledge.recommendation_execution_context_v1(execution_allowed, runtime_allowed, micro_live_allowed);
