INSERT INTO knowledge.platform_parameter_v1
(parameter_code, parameter_name, parameter_group, parameter_type, parameter_value, description, enabled, source_version)
VALUES
('PAPER_ANALYTICS_VALIDATED_MIN_TRADES', 'Paper analytics validated minimum trades', 'PAPER_ANALYTICS', 'INTEGER', '30', 'Minimum trades for VALIDATED status', TRUE, 'PAPER_EXECUTION_ANALYTICS_ENGINE_V1'),
('PAPER_ANALYTICS_PRODUCTION_MIN_TRADES', 'Paper analytics production minimum trades', 'PAPER_ANALYTICS', 'INTEGER', '100', 'Minimum trades for PRODUCTION status', TRUE, 'PAPER_EXECUTION_ANALYTICS_ENGINE_V1')
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
