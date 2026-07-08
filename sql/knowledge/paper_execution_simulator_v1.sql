CREATE TABLE IF NOT EXISTS knowledge.paper_execution_result_v1 (
    paper_result_id BIGSERIAL PRIMARY KEY,

    execution_context_id BIGINT NOT NULL
        REFERENCES knowledge.recommendation_execution_context_v1(execution_context_id)
        ON DELETE CASCADE,

    recommendation_id BIGINT NOT NULL
        REFERENCES knowledge.recommendation_result_v1(recommendation_id)
        ON DELETE CASCADE,

    symbol TEXT NOT NULL,
    timeframe TEXT NOT NULL,
    direction_code TEXT NOT NULL,

    entry_price NUMERIC NOT NULL,
    exit_price NUMERIC NOT NULL,
    invalidation_price NUMERIC NOT NULL,
    target_price NUMERIC NOT NULL,

    entry_ts TIMESTAMPTZ,
    exit_ts TIMESTAMPTZ,

    exit_reason TEXT NOT NULL,

    pnl_points NUMERIC NOT NULL,
    r_multiple NUMERIC NOT NULL,

    bars_held INTEGER NOT NULL,
    mae_points NUMERIC,
    mfe_points NUMERIC,

    evidence_json JSONB NOT NULL DEFAULT '{}'::jsonb,
    source_version TEXT NOT NULL,

    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_paper_execution_result_context_v1
ON knowledge.paper_execution_result_v1(execution_context_id);

CREATE INDEX IF NOT EXISTS idx_paper_execution_result_symbol_v1
ON knowledge.paper_execution_result_v1(symbol, timeframe, source_version);
