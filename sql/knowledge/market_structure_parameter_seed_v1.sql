INSERT INTO knowledge.market_structure_type_v1
(structure_type_code, structure_type_name, enabled, source_version)
VALUES
('SUPPORT', 'Support level', TRUE, 'MARKET_STRUCTURE_PARAMETER_SEED_V1'),
('RESISTANCE', 'Resistance level', TRUE, 'MARKET_STRUCTURE_PARAMETER_SEED_V1'),
('SWING_HIGH', 'Swing high', TRUE, 'MARKET_STRUCTURE_PARAMETER_SEED_V1'),
('SWING_LOW', 'Swing low', TRUE, 'MARKET_STRUCTURE_PARAMETER_SEED_V1'),
('PIVOT_LEVEL', 'Pivot level', TRUE, 'MARKET_STRUCTURE_PARAMETER_SEED_V1'),
('FIBONACCI_RETRACEMENT', 'Fibonacci retracement level', TRUE, 'MARKET_STRUCTURE_PARAMETER_SEED_V1'),
('FIBONACCI_EXTENSION', 'Fibonacci extension level', TRUE, 'MARKET_STRUCTURE_PARAMETER_SEED_V1'),
('CHANNEL_UPPER', 'Channel upper level', TRUE, 'MARKET_STRUCTURE_PARAMETER_SEED_V1'),
('CHANNEL_LOWER', 'Channel lower level', TRUE, 'MARKET_STRUCTURE_PARAMETER_SEED_V1'),
('BREAKOUT_LEVEL', 'Breakout level', TRUE, 'MARKET_STRUCTURE_PARAMETER_SEED_V1')
ON CONFLICT(structure_type_code)
DO UPDATE SET
  structure_type_name=EXCLUDED.structure_type_name,
  enabled=EXCLUDED.enabled,
  source_version=EXCLUDED.source_version,
  updated_at=now();

INSERT INTO knowledge.platform_parameter_v1
(parameter_code, parameter_name, parameter_group, parameter_type, parameter_value, description, enabled, source_version)
VALUES
('MARKET_STRUCTURE_LOOKBACK_BARS', 'Market structure lookback bars', 'MARKET_STRUCTURE', 'INTEGER', '120', 'Lookback bars for structure detection', TRUE, 'MARKET_STRUCTURE_PARAMETER_SEED_V1'),
('MARKET_STRUCTURE_SWING_WINDOW', 'Market structure swing window', 'MARKET_STRUCTURE', 'INTEGER', '3', 'Bars around local swing point', TRUE, 'MARKET_STRUCTURE_PARAMETER_SEED_V1'),
('MARKET_STRUCTURE_MIN_TOUCHES', 'Market structure minimum touches', 'MARKET_STRUCTURE', 'INTEGER', '2', 'Minimum touches for level strength', TRUE, 'MARKET_STRUCTURE_PARAMETER_SEED_V1'),
('MARKET_STRUCTURE_FIB_RETRACEMENTS', 'Fibonacci retracement ratios', 'MARKET_STRUCTURE', 'TEXT', '0.236,0.382,0.500,0.618,0.786', 'Configured Fibonacci retracement ratios', TRUE, 'MARKET_STRUCTURE_PARAMETER_SEED_V1'),
('MARKET_STRUCTURE_FIB_EXTENSIONS', 'Fibonacci extension ratios', 'MARKET_STRUCTURE', 'TEXT', '1.272,1.618,2.000', 'Configured Fibonacci extension ratios', TRUE, 'MARKET_STRUCTURE_PARAMETER_SEED_V1')
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
