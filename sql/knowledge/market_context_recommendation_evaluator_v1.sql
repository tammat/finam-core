CREATE TABLE IF NOT EXISTS knowledge.recommendation_rule_condition_v1 (
    condition_id BIGSERIAL PRIMARY KEY,
    rule_code TEXT NOT NULL,
    metric_code TEXT NOT NULL,
    operator_code TEXT NOT NULL CHECK (operator_code IN ('GE','GT','LE','LT','EQ','NE')),
    parameter_code TEXT NOT NULL,
    enabled BOOLEAN NOT NULL DEFAULT TRUE,
    condition_order INTEGER NOT NULL DEFAULT 100,
    source_version TEXT NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE(rule_code, metric_code, operator_code, parameter_code, source_version)
);

CREATE INDEX IF NOT EXISTS idx_recommendation_rule_condition_v1
ON knowledge.recommendation_rule_condition_v1(rule_code, enabled, condition_order);

INSERT INTO knowledge.recommendation_rule_condition_v1
(rule_code, metric_code, operator_code, parameter_code, enabled, condition_order, source_version)
SELECT 'RULE_VALIDATE_DEFAULT', 'EDGE_SCORE', 'GE', 'EDGE_VALIDATE_THRESHOLD', TRUE, 100, 'MARKET_CONTEXT_RECOMMENDATION_EVALUATOR_V1'
ON CONFLICT(rule_code, metric_code, operator_code, parameter_code, source_version)
DO UPDATE SET enabled=EXCLUDED.enabled, updated_at=now();

INSERT INTO knowledge.recommendation_rule_condition_v1
(rule_code, metric_code, operator_code, parameter_code, enabled, condition_order, source_version)
SELECT 'RULE_VALIDATE_DEFAULT', 'KNOWLEDGE_COVERAGE', 'GE', 'KNOWLEDGE_MIN_THRESHOLD', TRUE, 200, 'MARKET_CONTEXT_RECOMMENDATION_EVALUATOR_V1'
ON CONFLICT(rule_code, metric_code, operator_code, parameter_code, source_version)
DO UPDATE SET enabled=EXCLUDED.enabled, updated_at=now();

INSERT INTO knowledge.recommendation_rule_condition_v1
(rule_code, metric_code, operator_code, parameter_code, enabled, condition_order, source_version)
SELECT 'RULE_CONTINUE_RESEARCH', 'EDGE_SCORE', 'GE', 'EDGE_RESEARCH_THRESHOLD', TRUE, 100, 'MARKET_CONTEXT_RECOMMENDATION_EVALUATOR_V1'
ON CONFLICT(rule_code, metric_code, operator_code, parameter_code, source_version)
DO UPDATE SET enabled=EXCLUDED.enabled, updated_at=now();

INSERT INTO knowledge.recommendation_rule_condition_v1
(rule_code, metric_code, operator_code, parameter_code, enabled, condition_order, source_version)
SELECT 'RULE_OBSERVE', 'EDGE_SCORE', 'GE', 'EDGE_OBSERVE_THRESHOLD', TRUE, 100, 'MARKET_CONTEXT_RECOMMENDATION_EVALUATOR_V1'
ON CONFLICT(rule_code, metric_code, operator_code, parameter_code, source_version)
DO UPDATE SET enabled=EXCLUDED.enabled, updated_at=now();
