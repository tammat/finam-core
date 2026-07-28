BEGIN;

INSERT INTO analytics.runtime_strategy_assignment_v1 (
    symbol, timeframe, asset_group, strategy_code, generator_code, priority,
    countertrend_long_allowed, commission_bps, spread_bps, slippage_bps,
    min_edge_buffer_bps, assignment_reason
)
VALUES
    ('SBER@MISX',  'M5', 'EQUITY', 'VOLATILITY_BREAKOUT_EQUITY', 'EQUITY_ASSIGNED_GENERATOR_V1', 85, false, 8, 8, 7, 7, 'Основная исследовательская акция'),
    ('SBERP@MISX', 'M5', 'EQUITY', 'VOLATILITY_BREAKOUT_EQUITY', 'EQUITY_ASSIGNED_GENERATOR_V1', 75, false, 8, 9, 7, 7, 'Исследовательская акция'),
    ('GAZP@MISX',  'M5', 'EQUITY', 'VOLATILITY_BREAKOUT_EQUITY', 'EQUITY_ASSIGNED_GENERATOR_V1', 80, false, 8, 8, 7, 7, 'Основная исследовательская акция'),
    ('LKOH@MISX',  'M5', 'EQUITY', 'VOLATILITY_BREAKOUT_EQUITY', 'EQUITY_ASSIGNED_GENERATOR_V1', 80, false, 8, 8, 7, 7, 'Основная исследовательская акция'),
    ('NVTK@MISX',  'M5', 'EQUITY', 'VOLATILITY_BREAKOUT_EQUITY', 'EQUITY_ASSIGNED_GENERATOR_V1', 75, false, 8, 9, 8, 7, 'Основная исследовательская акция'),
    ('VTBR@MISX',  'M5', 'EQUITY', 'VOLATILITY_BREAKOUT_EQUITY', 'EQUITY_ASSIGNED_GENERATOR_V1', 70, false, 8, 10, 8, 8, 'Основная исследовательская акция'),
    ('PLZL@MISX',  'M5', 'EQUITY', 'VOLATILITY_BREAKOUT_EQUITY', 'EQUITY_ASSIGNED_GENERATOR_V1', 70, false, 8, 9, 8, 8, 'Исследовательская акция металлов')
ON CONFLICT (symbol, timeframe) DO UPDATE SET
    asset_group = EXCLUDED.asset_group,
    strategy_code = EXCLUDED.strategy_code,
    generator_code = EXCLUDED.generator_code,
    priority = EXCLUDED.priority,
    countertrend_long_allowed = EXCLUDED.countertrend_long_allowed,
    commission_bps = EXCLUDED.commission_bps,
    spread_bps = EXCLUDED.spread_bps,
    slippage_bps = EXCLUDED.slippage_bps,
    min_edge_buffer_bps = EXCLUDED.min_edge_buffer_bps,
    assignment_reason = EXCLUDED.assignment_reason,
    enabled = true,
    updated_at = clock_timestamp();

SELECT analytics.activate_instrument_with_strategy_policy_v2(
    a.symbol, a.timeframe, a.asset_group,
    'MEAN_REVERSION_EQUITY', 'EQUITY_MEAN_REVERSION_GENERATOR_V1',
    'VOLATILITY_BREAKOUT_EQUITY', 'EQUITY_VOLATILITY_BREAKOUT_GENERATOR_V1',
    a.priority, a.priority::numeric / 100, a.assignment_reason
)
FROM analytics.runtime_strategy_assignment_v1 a
WHERE a.enabled AND a.asset_group = 'EQUITY';

COMMIT;
