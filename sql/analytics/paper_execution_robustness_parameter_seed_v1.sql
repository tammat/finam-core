INSERT INTO knowledge.platform_parameter_v1
(parameter_code, parameter_name, parameter_group, parameter_type, parameter_value, description, enabled, source_version)
VALUES
('ROBUSTNESS_VALIDATED_MIN_TRADES', 'Validated minimum trades', 'PAPER_ROBUSTNESS', 'INTEGER', '30', 'Minimum trades for VALIDATED status', TRUE, 'PAPER_EXECUTION_ROBUSTNESS_AUDIT_V1'),
('ROBUSTNESS_PRODUCTION_MIN_TRADES', 'Production minimum trades', 'PAPER_ROBUSTNESS', 'INTEGER', '100', 'Minimum trades for PRODUCTION status', TRUE, 'PAPER_EXECUTION_ROBUSTNESS_AUDIT_V1'),
('ROBUSTNESS_MIN_TIME_BUCKETS', 'Minimum time buckets', 'PAPER_ROBUSTNESS', 'INTEGER', '3', 'Minimum time buckets for stability', TRUE, 'PAPER_EXECUTION_ROBUSTNESS_AUDIT_V1'),
('ROBUSTNESS_MIN_INSTRUMENTS', 'Minimum instruments', 'PAPER_ROBUSTNESS', 'INTEGER', '3', 'Minimum instruments for stability', TRUE, 'PAPER_EXECUTION_ROBUSTNESS_AUDIT_V1'),
('ROBUSTNESS_MIN_REGIMES', 'Minimum regimes', 'PAPER_ROBUSTNESS', 'INTEGER', '2', 'Minimum regimes for stability', TRUE, 'PAPER_EXECUTION_ROBUSTNESS_AUDIT_V1'),
('ROBUSTNESS_MIN_SOURCES', 'Minimum sources', 'PAPER_ROBUSTNESS', 'INTEGER', '2', 'Minimum source combinations for stability', TRUE, 'PAPER_EXECUTION_ROBUSTNESS_AUDIT_V1'),
('ROBUSTNESS_SCORE_MAX', 'Score maximum', 'PAPER_ROBUSTNESS', 'NUMERIC', '100', 'Maximum score value', TRUE, 'PAPER_EXECUTION_ROBUSTNESS_AUDIT_V1')
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
