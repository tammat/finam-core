BEGIN;

-- Repair legacy rows created before regime-aware routing became authoritative.
-- A sideways equity market must use mean reversion; a confirmed trend must use
-- volatility breakout.  Updating existing rows is essential: the original
-- bootstrap migration used ON CONFLICT DO NOTHING.
UPDATE analytics.runtime_strategy_policy_v2
SET strategy_code = 'MEAN_REVERSION_EQUITY',
    generator_code = 'EQUITY_MEAN_REVERSION_GENERATOR_V1',
    enabled = true,
    assignment_reason = 'Боковик: возврат к среднему по режимной политике',
    updated_at = clock_timestamp()
WHERE symbol LIKE '%@MISX'
  AND regime_family = 'RANGE'
  AND (
      strategy_code IS DISTINCT FROM 'MEAN_REVERSION_EQUITY'
      OR generator_code IS DISTINCT FROM 'EQUITY_MEAN_REVERSION_GENERATOR_V1'
      OR NOT enabled
  );

UPDATE analytics.runtime_strategy_policy_v2
SET strategy_code = 'VOLATILITY_BREAKOUT_EQUITY',
    generator_code = 'EQUITY_VOLATILITY_BREAKOUT_GENERATOR_V1',
    enabled = true,
    assignment_reason = 'Подтверждённый тренд: пробой волатильности по режимной политике',
    updated_at = clock_timestamp()
WHERE symbol LIKE '%@MISX'
  AND regime_family = 'TREND'
  AND (
      strategy_code IS DISTINCT FROM 'VOLATILITY_BREAKOUT_EQUITY'
      OR generator_code IS DISTINCT FROM 'EQUITY_VOLATILITY_BREAKOUT_GENERATOR_V1'
      OR NOT enabled
  );

COMMIT;
