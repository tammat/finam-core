BEGIN;

ALTER TABLE analytics.runtime_strategy_assignment_v1
    ADD COLUMN IF NOT EXISTS countertrend_short_allowed boolean NOT NULL DEFAULT false;

COMMENT ON COLUMN analytics.runtime_strategy_assignment_v1.countertrend_short_allowed IS
    'Разрешает SHORT против подтверждённого восходящего режима только специальной контртрендовой модели.';

INSERT INTO analytics.oos_branch_guard_v1 (
    symbol_pattern, strategy_code, side_code, session_code, regime_code,
    exit_rule, decision_code, reason_code
)
SELECT '*', strategy_code, side_code, '*', regime_code, '*', 'BLOCK', reason_code
FROM (VALUES
    ('VOLATILITY_BREAKOUT_EQUITY', 'SHORT', 'trend_up%', 'SHORT_IN_CONFIRMED_UPTREND_WITHOUT_COUNTERTREND_MODEL'),
    ('BR_CONSERVATIVE_BREAKOUT', 'SHORT', 'trend_up%', 'SHORT_IN_CONFIRMED_UPTREND_WITHOUT_COUNTERTREND_MODEL'),
    ('NG_CONSERVATIVE_BREAKOUT_M1', 'SHORT', 'trend_up%', 'SHORT_IN_CONFIRMED_UPTREND_WITHOUT_COUNTERTREND_MODEL')
) AS rules(strategy_code, side_code, regime_code, reason_code)
ON CONFLICT (symbol_pattern, strategy_code, side_code, session_code, regime_code, exit_rule)
DO UPDATE SET decision_code = EXCLUDED.decision_code,
              reason_code = EXCLUDED.reason_code,
              enabled = true,
              updated_at = clock_timestamp();

COMMIT;
