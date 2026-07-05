CREATE TABLE IF NOT EXISTS analytics.edge_discovery_method_v1 (
    method_code TEXT PRIMARY KEY,
    method_name TEXT NOT NULL,
    method_family TEXT NOT NULL,
    enabled BOOLEAN NOT NULL DEFAULT true,
    config_json JSONB NOT NULL DEFAULT '{}'::jsonb,
    source_version TEXT NOT NULL DEFAULT 'EDGE_DISCOVERY_ENGINE_FOUNDATION_V1',
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS analytics.edge_discovery_rule_v1 (
    id BIGSERIAL PRIMARY KEY,
    rule_code TEXT NOT NULL UNIQUE,
    method_code TEXT NOT NULL REFERENCES analytics.edge_discovery_method_v1(method_code),
    metric_name TEXT NOT NULL,
    operator_code TEXT NOT NULL,
    threshold_value NUMERIC(20,8),
    weight NUMERIC(12,6) NOT NULL DEFAULT 1,
    enabled BOOLEAN NOT NULL DEFAULT true,
    source_version TEXT NOT NULL DEFAULT 'EDGE_DISCOVERY_ENGINE_FOUNDATION_V1',
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS analytics.edge_discovery_run_v1 (
    id BIGSERIAL PRIMARY KEY,
    discovery_run_uuid UUID NOT NULL DEFAULT gen_random_uuid(),
    discovery_batch_id TEXT NOT NULL,
    method_code TEXT NOT NULL,
    status_code TEXT NOT NULL DEFAULT 'QUEUED',
    observations_scanned INTEGER NOT NULL DEFAULT 0,
    candidates_created INTEGER NOT NULL DEFAULT 0,
    source_version TEXT NOT NULL DEFAULT 'EDGE_DISCOVERY_ENGINE_FOUNDATION_V1',
    started_at TIMESTAMPTZ,
    finished_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

INSERT INTO analytics.edge_discovery_method_v1(method_code, method_name, method_family, enabled, config_json)
VALUES
('RULE_RANK_V1', 'Rule based ranking', 'RULE_ENGINE', true, '{"candidate_limit":100}'::jsonb),
('PARETO_V1', 'Pareto front placeholder', 'MULTI_OBJECTIVE', false, '{}'::jsonb),
('GRID_OBJECTIVE_V1', 'Grid objective placeholder', 'PARAMETER_SEARCH', false, '{}'::jsonb),
('BAYESIAN_V1', 'Bayesian optimization placeholder', 'OPTIMIZATION', false, '{}'::jsonb),
('GENETIC_V1', 'Genetic search placeholder', 'OPTIMIZATION', false, '{}'::jsonb)
ON CONFLICT(method_code) DO UPDATE SET
    method_name=EXCLUDED.method_name,
    method_family=EXCLUDED.method_family,
    config_json=EXCLUDED.config_json,
    updated_at=now();

INSERT INTO analytics.edge_discovery_rule_v1(rule_code, method_code, metric_name, operator_code, threshold_value, weight, enabled)
VALUES
('RULE_TRADES_MIN_V1', 'RULE_RANK_V1', 'trades', '>=', 30, 0.20, true),
('RULE_PF_MIN_V1', 'RULE_RANK_V1', 'profit_factor', '>=', 1.20, 0.25, true),
('RULE_EXPECTANCY_POSITIVE_V1', 'RULE_RANK_V1', 'expectancy', '>', 0, 0.20, true),
('RULE_SCORE_MIN_V1', 'RULE_RANK_V1', 'normalized_edge_score', '>=', 60, 0.20, true),
('RULE_CONFIDENCE_MIN_V1', 'RULE_RANK_V1', 'confidence_score', '>=', 60, 0.10, true),
('RULE_STABILITY_MIN_V1', 'RULE_RANK_V1', 'stability_score', '>=', 60, 0.05, true)
ON CONFLICT(rule_code) DO UPDATE SET
    method_code=EXCLUDED.method_code,
    metric_name=EXCLUDED.metric_name,
    operator_code=EXCLUDED.operator_code,
    threshold_value=EXCLUDED.threshold_value,
    weight=EXCLUDED.weight,
    enabled=EXCLUDED.enabled,
    updated_at=now();

GRANT SELECT, INSERT, UPDATE, DELETE ON analytics.edge_discovery_method_v1 TO alex;
GRANT SELECT, INSERT, UPDATE, DELETE ON analytics.edge_discovery_rule_v1 TO alex;
GRANT SELECT, INSERT, UPDATE, DELETE ON analytics.edge_discovery_run_v1 TO alex;
GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA analytics TO alex;
