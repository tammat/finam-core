INSERT INTO knowledge.platform_parameter_v1
(parameter_code, parameter_name, parameter_group, parameter_type, parameter_value, description, enabled, source_version)
VALUES
('TRADING_PLAN_ACTIVE_PROFILE', 'Active trading plan profile', 'TRADING_PLAN', 'TEXT', 'PROFILE_DEFAULT', 'Active profile for Trading Plan Builder', TRUE, 'TRADING_PLAN_PARAMETER_BUILDER_V1'),
('TRADING_PLAN_HORIZON_BARS', 'Trading plan horizon bars', 'TRADING_PLAN', 'INTEGER', '24', 'Default paper validation horizon in bars', TRUE, 'TRADING_PLAN_PARAMETER_BUILDER_V1'),
('TRADING_PLAN_RISK_UNIT', 'Trading plan risk unit', 'TRADING_PLAN', 'NUMERIC', '1', 'Default risk unit for R-multiple calculation', TRUE, 'TRADING_PLAN_PARAMETER_BUILDER_V1')
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
