ALTER TABLE analytics.marketcore_model_health_component_registry_v1
ADD COLUMN IF NOT EXISTS metric_table TEXT;

ALTER TABLE analytics.marketcore_model_health_component_registry_v1
ADD COLUMN IF NOT EXISTS metric_column TEXT;

ALTER TABLE analytics.marketcore_model_health_component_registry_v1
ADD COLUMN IF NOT EXISTS aggregation_method TEXT;

UPDATE analytics.marketcore_model_health_component_registry_v1
SET
  metric_table = 'analytics.paper_execution_robustness_audit_v1',
  metric_column = 'robustness_score',
  aggregation_method = 'LAST'
WHERE component_code='ROBUSTNESS';

UPDATE analytics.marketcore_model_health_component_registry_v1
SET
  metric_table = 'analytics.paper_execution_robustness_audit_v1',
  metric_column = 'learning_readiness_index',
  aggregation_method = 'LAST'
WHERE component_code='LEARNING_READINESS';

UPDATE analytics.marketcore_model_health_component_registry_v1
SET
  metric_table = 'knowledge.recommendation_execution_context_v1',
  metric_column = 'execution_context_id',
  aggregation_method = 'COVERAGE'
WHERE component_code='TRADING_PLAN_COMPLETENESS';

UPDATE analytics.marketcore_model_health_component_registry_v1
SET
  metric_table = 'knowledge.paper_execution_result_v1',
  metric_column = 'paper_result_id',
  aggregation_method = 'COVERAGE'
WHERE component_code='PAPER_COVERAGE';

UPDATE analytics.marketcore_model_health_component_registry_v1
SET
  metric_table = 'analytics.paper_execution_feedback_v1',
  metric_column = 'feedback_id',
  aggregation_method = 'COUNT'
WHERE component_code='FEEDBACK_READINESS';

UPDATE analytics.marketcore_model_health_component_registry_v1
SET
  metric_table = 'knowledge.market_structure_v1',
  metric_column = 'structure_id',
  aggregation_method = 'COVERAGE'
WHERE component_code='MARKET_MODEL_QUALITY';

UPDATE analytics.marketcore_model_health_component_registry_v1
SET
  metric_table = 'knowledge.market_structure_v1',
  metric_column = 'structure_id',
  aggregation_method = 'COVERAGE'
WHERE component_code='KNOWLEDGE_CONFIDENCE';

UPDATE analytics.marketcore_model_health_component_registry_v1
SET
  metric_table = 'analytics.paper_execution_robustness_audit_v1',
  metric_column = 'production_allowed',
  aggregation_method = 'LAST_BINARY'
WHERE component_code='PRODUCTION_READINESS';
