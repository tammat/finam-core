CREATE TABLE IF NOT EXISTS knowledge.recommendation_rule_v1 (
    rule_id              BIGSERIAL PRIMARY KEY,
    rule_code            TEXT NOT NULL UNIQUE,
    rule_name            TEXT NOT NULL,

    priority             INTEGER NOT NULL,

    enabled              BOOLEAN NOT NULL DEFAULT TRUE,

    effective_from       TIMESTAMPTZ NOT NULL DEFAULT now(),
    effective_to         TIMESTAMPTZ,

    recommendation_code  TEXT NOT NULL,

    parameter_profile    TEXT NOT NULL,

    rule_version         INTEGER NOT NULL DEFAULT 1,

    source_version       TEXT NOT NULL,

    created_at           TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at           TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS knowledge.recommendation_result_v1 (
    recommendation_id        BIGSERIAL PRIMARY KEY,

    symbol                   TEXT NOT NULL,

    timeframe                TEXT NOT NULL,

    recommendation_code      TEXT NOT NULL,

    recommendation_confidence NUMERIC NOT NULL,

    rule_code                TEXT NOT NULL,

    knowledge_version        TEXT NOT NULL,

    evidence_json            JSONB NOT NULL DEFAULT '{}'::jsonb,

    source_version           TEXT NOT NULL,

    created_at               TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS knowledge.recommendation_reason_v1 (
    reason_id            BIGSERIAL PRIMARY KEY,

    recommendation_id    BIGINT NOT NULL
                          REFERENCES knowledge.recommendation_result_v1(recommendation_id)
                          ON DELETE CASCADE,

    reason_order         INTEGER NOT NULL,

    reason_code          TEXT NOT NULL,

    reason_value         TEXT,

    confidence           NUMERIC,

    source_version       TEXT NOT NULL,

    created_at           TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_recommendation_result_symbol
ON knowledge.recommendation_result_v1(symbol,timeframe);

CREATE INDEX IF NOT EXISTS idx_recommendation_rule_priority
ON knowledge.recommendation_rule_v1(priority,enabled);

CREATE INDEX IF NOT EXISTS idx_recommendation_reason_parent
ON knowledge.recommendation_reason_v1(recommendation_id);
