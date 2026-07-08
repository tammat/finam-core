CREATE TABLE IF NOT EXISTS knowledge.paper_execution_validation_v1 (
    validation_id BIGSERIAL PRIMARY KEY,
    recommendation_id BIGINT NOT NULL,
    symbol TEXT NOT NULL,
    timeframe TEXT NOT NULL,
    recommendation_code TEXT NOT NULL,
    validation_status TEXT NOT NULL,
    validation_reason TEXT NOT NULL,
    bars_after_recommendation INTEGER NOT NULL DEFAULT 0,
    source_version TEXT NOT NULL,
    evidence_json JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_paper_execution_validation_recommendation_v1
ON knowledge.paper_execution_validation_v1(recommendation_id);

CREATE INDEX IF NOT EXISTS idx_paper_execution_validation_symbol_v1
ON knowledge.paper_execution_validation_v1(symbol, timeframe);
