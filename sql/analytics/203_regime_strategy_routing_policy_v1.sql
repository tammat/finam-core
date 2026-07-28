BEGIN;

CREATE TABLE IF NOT EXISTS analytics.regime_strategy_routing_policy_v1 (
    asset_group text NOT NULL,
    regime_trend text NOT NULL,
    strategy_code text NOT NULL,
    allowed_side text NOT NULL CHECK (allowed_side IN ('BUY', 'SELL', 'BOTH')),
    countertrend_allowed boolean NOT NULL DEFAULT false,
    minimum_cost_buffer numeric(8, 4) NOT NULL DEFAULT 1.5,
    exit_policy_code text NOT NULL DEFAULT 'DYNAMIC_EXIT_V1',
    max_holding_bars integer NOT NULL DEFAULT 20 CHECK (max_holding_bars BETWEEN 1 AND 20),
    active boolean NOT NULL DEFAULT true,
    updated_at timestamptz NOT NULL DEFAULT now(),
    PRIMARY KEY (asset_group, regime_trend)
);

INSERT INTO analytics.regime_strategy_routing_policy_v1 (
    asset_group, regime_trend, strategy_code, allowed_side,
    countertrend_allowed, minimum_cost_buffer, exit_policy_code, max_holding_bars
)
VALUES
    ('EQUITY', 'range',      'MEAN_REVERSION_EQUITY',      'BOTH', false, 1.5, 'DYNAMIC_EXIT_V1', 20),
    ('EQUITY', 'trend_up',   'VOLATILITY_BREAKOUT_EQUITY', 'BUY',  false, 1.5, 'DYNAMIC_EXIT_V1', 20),
    ('EQUITY', 'trend_down', 'VOLATILITY_BREAKOUT_EQUITY', 'SELL', false, 1.5, 'DYNAMIC_EXIT_V1', 20)
    ,('FUTURES_BR', 'trend_up',   'BR_CONSERVATIVE_BREAKOUT', 'BUY',  false, 1.5, 'DYNAMIC_EXIT_V1', 20)
    ,('FUTURES_BR', 'trend_down', 'BR_CONSERVATIVE_BREAKOUT', 'SELL', false, 1.5, 'DYNAMIC_EXIT_V1', 20)
    ,('FUTURES_NG', 'trend_up',   'NG_CONSERVATIVE_BREAKOUT_M1', 'BUY',  false, 1.5, 'DYNAMIC_EXIT_V1', 20)
    ,('FUTURES_NG', 'trend_down', 'NG_CONSERVATIVE_BREAKOUT_M1', 'SELL', false, 1.5, 'DYNAMIC_EXIT_V1', 20)
    ,('FUTURES_CNY', 'trend_up',   'CNY_REGIME_FUTURES', 'BUY',  false, 1.5, 'DYNAMIC_EXIT_V1', 20)
    ,('FUTURES_CNY', 'trend_down', 'CNY_REGIME_FUTURES', 'SELL', false, 1.5, 'DYNAMIC_EXIT_V1', 20)
    ,('FUTURES_USD', 'trend_up',   'USD_REGIME_FUTURES', 'BUY',  false, 1.5, 'DYNAMIC_EXIT_V1', 20)
    ,('FUTURES_USD', 'trend_down', 'USD_REGIME_FUTURES', 'SELL', false, 1.5, 'DYNAMIC_EXIT_V1', 20)
    ,('FUTURES_GOLD', 'trend_up',   'GOLD_TREND_BREAKOUT', 'BUY',  false, 1.5, 'DYNAMIC_EXIT_V1', 20)
    ,('FUTURES_GOLD', 'trend_down', 'GOLD_TREND_BREAKOUT', 'SELL', false, 1.5, 'DYNAMIC_EXIT_V1', 20)
ON CONFLICT (asset_group, regime_trend) DO UPDATE SET
    strategy_code = EXCLUDED.strategy_code,
    allowed_side = EXCLUDED.allowed_side,
    countertrend_allowed = EXCLUDED.countertrend_allowed,
    minimum_cost_buffer = EXCLUDED.minimum_cost_buffer,
    exit_policy_code = EXCLUDED.exit_policy_code,
    max_holding_bars = EXCLUDED.max_holding_bars,
    active = true,
    updated_at = now();

COMMENT ON TABLE analytics.regime_strategy_routing_policy_v1 IS
'DB-политика выбора стратегии и допустимой стороны по подтверждённому режиму. Не изменяет критерии OOS PASS.';

COMMIT;
