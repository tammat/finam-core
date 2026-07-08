CREATE TABLE IF NOT EXISTS analytics.marketcore_model_health_component_registry_v1 (
    component_code TEXT PRIMARY KEY,
    component_name TEXT NOT NULL,
    component_group TEXT NOT NULL,
    metric_source TEXT NOT NULL,
    weight_parameter_code TEXT NOT NULL,
    enabled BOOLEAN NOT NULL DEFAULT TRUE,
    source_version TEXT NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

INSERT INTO analytics.marketcore_model_health_component_registry_v1
(component_code, component_name, component_group, metric_source, weight_parameter_code, enabled, source_version)
VALUES
('MARKET_MODEL_QUALITY', 'Market Model Quality Index', 'MODEL_HEALTH', 'KNOWLEDGE_LAYER', 'MODEL_HEALTH_WEIGHT_MARKET_MODEL_QUALITY', TRUE, 'MARKETCORE_MODEL_HEALTH_REGISTRY_V1'),
('LEARNING_READINESS', 'Learning Readiness Index', 'MODEL_HEALTH', 'ROBUSTNESS_LAYER', 'MODEL_HEALTH_WEIGHT_LEARNING_READINESS', TRUE, 'MARKETCORE_MODEL_HEALTH_REGISTRY_V1'),
('ROBUSTNESS', 'Robustness Score', 'MODEL_HEALTH', 'ROBUSTNESS_LAYER', 'MODEL_HEALTH_WEIGHT_ROBUSTNESS', TRUE, 'MARKETCORE_MODEL_HEALTH_REGISTRY_V1'),
('KNOWLEDGE_CONFIDENCE', 'Knowledge Confidence Index', 'MODEL_HEALTH', 'KNOWLEDGE_LAYER', 'MODEL_HEALTH_WEIGHT_KNOWLEDGE_CONFIDENCE', TRUE, 'MARKETCORE_MODEL_HEALTH_REGISTRY_V1'),
('TRADING_PLAN_COMPLETENESS', 'Trading Plan Completeness', 'MODEL_HEALTH', 'TRADING_PLAN_LAYER', 'MODEL_HEALTH_WEIGHT_TRADING_PLAN_COMPLETENESS', TRUE, 'MARKETCORE_MODEL_HEALTH_REGISTRY_V1'),
('PAPER_COVERAGE', 'Paper Coverage', 'MODEL_HEALTH', 'PAPER_LAYER', 'MODEL_HEALTH_WEIGHT_PAPER_COVERAGE', TRUE, 'MARKETCORE_MODEL_HEALTH_REGISTRY_V1'),
('FEEDBACK_READINESS', 'Feedback Readiness', 'MODEL_HEALTH', 'FEEDBACK_LAYER', 'MODEL_HEALTH_WEIGHT_FEEDBACK_READINESS', TRUE, 'MARKETCORE_MODEL_HEALTH_REGISTRY_V1'),
('PRODUCTION_READINESS', 'Production Readiness', 'MODEL_HEALTH', 'GATE_LAYER', 'MODEL_HEALTH_WEIGHT_PRODUCTION_READINESS', TRUE, 'MARKETCORE_MODEL_HEALTH_REGISTRY_V1')
ON CONFLICT(component_code)
DO UPDATE SET
  component_name=EXCLUDED.component_name,
  component_group=EXCLUDED.component_group,
  metric_source=EXCLUDED.metric_source,
  weight_parameter_code=EXCLUDED.weight_parameter_code,
  enabled=EXCLUDED.enabled,
  source_version=EXCLUDED.source_version,
  updated_at=now();

INSERT INTO knowledge.platform_parameter_v1
(parameter_code, parameter_name, parameter_group, parameter_type, parameter_value, description, enabled, source_version)
VALUES
('MODEL_HEALTH_WEIGHT_MARKET_MODEL_QUALITY', 'Weight: Market Model Quality', 'MODEL_HEALTH', 'NUMERIC', '1', 'Weight for Market Model Quality component', TRUE, 'MARKETCORE_MODEL_HEALTH_REGISTRY_V1'),
('MODEL_HEALTH_WEIGHT_LEARNING_READINESS', 'Weight: Learning Readiness', 'MODEL_HEALTH', 'NUMERIC', '1', 'Weight for Learning Readiness component', TRUE, 'MARKETCORE_MODEL_HEALTH_REGISTRY_V1'),
('MODEL_HEALTH_WEIGHT_ROBUSTNESS', 'Weight: Robustness', 'MODEL_HEALTH', 'NUMERIC', '1', 'Weight for Robustness component', TRUE, 'MARKETCORE_MODEL_HEALTH_REGISTRY_V1'),
('MODEL_HEALTH_WEIGHT_KNOWLEDGE_CONFIDENCE', 'Weight: Knowledge Confidence', 'MODEL_HEALTH', 'NUMERIC', '1', 'Weight for Knowledge Confidence component', TRUE, 'MARKETCORE_MODEL_HEALTH_REGISTRY_V1'),
('MODEL_HEALTH_WEIGHT_TRADING_PLAN_COMPLETENESS', 'Weight: Trading Plan Completeness', 'MODEL_HEALTH', 'NUMERIC', '1', 'Weight for Trading Plan Completeness component', TRUE, 'MARKETCORE_MODEL_HEALTH_REGISTRY_V1'),
('MODEL_HEALTH_WEIGHT_PAPER_COVERAGE', 'Weight: Paper Coverage', 'MODEL_HEALTH', 'NUMERIC', '1', 'Weight for Paper Coverage component', TRUE, 'MARKETCORE_MODEL_HEALTH_REGISTRY_V1'),
('MODEL_HEALTH_WEIGHT_FEEDBACK_READINESS', 'Weight: Feedback Readiness', 'MODEL_HEALTH', 'NUMERIC', '1', 'Weight for Feedback Readiness component', TRUE, 'MARKETCORE_MODEL_HEALTH_REGISTRY_V1'),
('MODEL_HEALTH_WEIGHT_PRODUCTION_READINESS', 'Weight: Production Readiness', 'MODEL_HEALTH', 'NUMERIC', '1', 'Weight for Production Readiness component', TRUE, 'MARKETCORE_MODEL_HEALTH_REGISTRY_V1')
ON CONFLICT(parameter_code)
DO UPDATE SET
  parameter_name=EXCLUDED.parameter_name,
  parameter_group=EXCLUDED.parameter_group,
  parameter_type=EXCLUDED.parameter_type,
  parameter_value=EXCLUDED.parameter_value,
  description=EXCLUDED.description,
  enabled=EXCLUDED.enabled,
  source_version=EXCLUDED.source_version,
  updated_at=now();
