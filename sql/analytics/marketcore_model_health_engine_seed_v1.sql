INSERT INTO knowledge.platform_parameter_v1
(parameter_code, parameter_name, parameter_group, parameter_type, parameter_value, description, enabled, source_version)
VALUES
('MODEL_HEALTH_SCORE_MAX', 'Model health score maximum', 'MODEL_HEALTH', 'NUMERIC', '100', 'Maximum model health score', TRUE, 'MARKETCORE_MODEL_HEALTH_ENGINE_V1'),
('MODEL_HEALTH_STATUS_PASS_MIN', 'Model health PASS threshold', 'MODEL_HEALTH', 'NUMERIC', '80', 'Minimum score for PASS status', TRUE, 'MARKETCORE_MODEL_HEALTH_ENGINE_V1'),
('MODEL_HEALTH_STATUS_WARNING_MIN', 'Model health WARNING threshold', 'MODEL_HEALTH', 'NUMERIC', '50', 'Minimum score for WARNING status', TRUE, 'MARKETCORE_MODEL_HEALTH_ENGINE_V1')
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
