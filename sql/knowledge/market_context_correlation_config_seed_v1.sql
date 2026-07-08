INSERT INTO knowledge.correlation_rule_v1
(rule_code, relation_type, timeframe, lookback_bars, min_observations, min_abs_correlation, is_active, source_version)
VALUES
('DEFAULT_M5', 'CORRELATION', 'M5', 50, 50, 0.70, TRUE, 'MARKET_CONTEXT_CORRELATION_CONFIG_SEED_V1'),
('DEFAULT_H1', 'CORRELATION', 'H1', 100, 100, 0.70, TRUE, 'MARKET_CONTEXT_CORRELATION_CONFIG_SEED_V1'),
('DEFAULT_D1', 'CORRELATION', 'D1', 250, 250, 0.70, TRUE, 'MARKET_CONTEXT_CORRELATION_CONFIG_SEED_V1')
ON CONFLICT(rule_code)
DO UPDATE SET
  relation_type=EXCLUDED.relation_type,
  timeframe=EXCLUDED.timeframe,
  lookback_bars=EXCLUDED.lookback_bars,
  min_observations=EXCLUDED.min_observations,
  min_abs_correlation=EXCLUDED.min_abs_correlation,
  is_active=EXCLUDED.is_active,
  updated_at=now(),
  source_version=EXCLUDED.source_version;

INSERT INTO knowledge.correlation_universe_v1
(source_symbol, target_symbol, timeframe, is_active, source_version)
SELECT DISTINCT
  a.symbol,
  b.symbol,
  r.timeframe,
  TRUE,
  'MARKET_CONTEXT_CORRELATION_CONFIG_SEED_V1'
FROM knowledge.instrument_v1 a
JOIN knowledge.instrument_v1 b
  ON a.symbol < b.symbol
JOIN knowledge.correlation_rule_v1 r
  ON r.is_active
WHERE a.is_active
  AND b.is_active
  AND r.source_version='MARKET_CONTEXT_CORRELATION_CONFIG_SEED_V1'
ON CONFLICT(source_symbol, target_symbol, timeframe, source_version)
DO UPDATE SET
  is_active=EXCLUDED.is_active,
  updated_at=now();
