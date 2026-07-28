BEGIN;

CREATE SCHEMA IF NOT EXISTS analytics;

CREATE TABLE IF NOT EXISTS analytics.runtime_strategy_assignment_v1 (
    symbol text NOT NULL,
    timeframe text NOT NULL,
    asset_group text NOT NULL CHECK (asset_group IN ('EQUITY', 'FUTURES')),
    strategy_code text NOT NULL,
    generator_code text NOT NULL,
    enabled boolean NOT NULL DEFAULT true,
    priority integer NOT NULL DEFAULT 50,
    countertrend_long_allowed boolean NOT NULL DEFAULT false,
    commission_bps numeric NOT NULL CHECK (commission_bps >= 0),
    spread_bps numeric NOT NULL CHECK (spread_bps >= 0),
    slippage_bps numeric NOT NULL CHECK (slippage_bps >= 0),
    min_edge_buffer_bps numeric NOT NULL DEFAULT 0 CHECK (min_edge_buffer_bps >= 0),
    assignment_reason text NOT NULL,
    updated_at timestamptz NOT NULL DEFAULT clock_timestamp(),
    PRIMARY KEY (symbol, timeframe)
);

COMMENT ON TABLE analytics.runtime_strategy_assignment_v1 IS
    'Единый DB-контракт назначения генератора и стратегии. Отсутствие строки означает запрет генерации.';

CREATE TABLE IF NOT EXISTS analytics.oos_branch_guard_v1 (
    guard_id bigserial PRIMARY KEY,
    symbol_pattern text NOT NULL,
    strategy_code text NOT NULL,
    side_code text NOT NULL DEFAULT '*',
    session_code text NOT NULL DEFAULT '*',
    regime_code text NOT NULL DEFAULT '*',
    exit_rule text NOT NULL DEFAULT '*',
    decision_code text NOT NULL CHECK (decision_code IN ('ALLOW', 'BLOCK')),
    reason_code text NOT NULL,
    enabled boolean NOT NULL DEFAULT true,
    created_at timestamptz NOT NULL DEFAULT clock_timestamp(),
    updated_at timestamptz NOT NULL DEFAULT clock_timestamp(),
    UNIQUE (symbol_pattern, strategy_code, side_code, session_code, regime_code, exit_rule)
);

COMMENT ON TABLE analytics.oos_branch_guard_v1 IS
    'Аудируемый запрет постановки конкретной убыточной ветки в OOS без ослабления PASS.';

INSERT INTO analytics.runtime_strategy_assignment_v1 (
    symbol, timeframe, asset_group, strategy_code, generator_code, priority,
    countertrend_long_allowed, commission_bps, spread_bps, slippage_bps,
    min_edge_buffer_bps, assignment_reason
)
VALUES
    ('BRQ6@RTSX', 'M5', 'FUTURES', 'BR_CONSERVATIVE_BREAKOUT', 'BR_FUTURES_GENERATOR_V1', 100, false, 3, 4, 4, 4, 'Отдельный генератор нефти'),
    ('NGQ6@RTSX', 'M1', 'FUTURES', 'NG_CONSERVATIVE_BREAKOUT_M1', 'NG_FUTURES_GENERATOR_V1', 95, false, 3, 6, 5, 5, 'Отдельный генератор газа'),
    ('EUTR@MISX', 'M5', 'EQUITY', 'VOLATILITY_BREAKOUT_EQUITY', 'EQUITY_ASSIGNED_GENERATOR_V1', 70, false, 8, 8, 7, 7, 'Явное назначение текущей исследовательской ветки'),
    ('OZON@MISX', 'M5', 'EQUITY', 'VOLATILITY_BREAKOUT_EQUITY', 'EQUITY_ASSIGNED_GENERATOR_V1', 60, false, 8, 10, 8, 7, 'Явное назначение текущей исследовательской ветки'),
    ('SFIN@MISX', 'M5', 'EQUITY', 'VOLATILITY_BREAKOUT_EQUITY', 'EQUITY_ASSIGNED_GENERATOR_V1', 60, false, 8, 10, 8, 7, 'Явное назначение текущей исследовательской ветки'),
    ('T@MISX', 'M5', 'EQUITY', 'VOLATILITY_BREAKOUT_EQUITY', 'EQUITY_ASSIGNED_GENERATOR_V1', 60, false, 8, 8, 7, 7, 'Явное назначение текущей исследовательской ветки'),
    ('X5@MISX', 'M5', 'EQUITY', 'VOLATILITY_BREAKOUT_EQUITY', 'EQUITY_ASSIGNED_GENERATOR_V1', 10, false, 8, 12, 10, 10, 'Аномальная ветка; только контролируемое накопление')
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
    updated_at = clock_timestamp();

INSERT INTO analytics.oos_branch_guard_v1 (
    symbol_pattern, strategy_code, side_code, session_code, regime_code,
    exit_rule, decision_code, reason_code
)
VALUES (
    '*', 'VOLATILITY_BREAKOUT_EQUITY', 'LONG', '*', 'trend_down%', '*',
    'BLOCK', 'NEGATIVE_EXPECTANCY_LONG_IN_CONFIRMED_DOWNTREND'
)
ON CONFLICT (symbol_pattern, strategy_code, side_code, session_code, regime_code, exit_rule)
DO UPDATE SET
    decision_code = EXCLUDED.decision_code,
    reason_code = EXCLUDED.reason_code,
    enabled = true,
    updated_at = clock_timestamp();

COMMIT;
