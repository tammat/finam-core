INSERT INTO knowledge.platform_parameter_v1
(parameter_code, parameter_name, parameter_group, parameter_type, parameter_value, description, enabled, source_version)
VALUES
('PAPER_VALIDATION_MIN_FUTURE_BARS', 'Minimum future bars for paper validation', 'PAPER_VALIDATION', 'INTEGER', '10', 'Minimum number of bars after recommendation timestamp', TRUE, 'PAPER_EXECUTION_VALIDATION_V1')
ON CONFLICT(parameter_code)
DO UPDATE SET
  parameter_name=EXCLUDED.parameter_name,
  parameter_group=EXCLUDED.parameter_group,
  parameter_type=EXCLUDED.parameter_type,
  parameter_value=EXCLUDED.parameter_value,
  description=EXCLUDED.description,
  enabled=EXCLUDED.enabled,
  updated_at=now(),
  source_version=EXCLUDED.source_version;
