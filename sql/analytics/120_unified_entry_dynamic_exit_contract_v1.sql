BEGIN;

CREATE TABLE IF NOT EXISTS analytics.research_entry_exit_contract_v1 (
    scope_code text NOT NULL CHECK(scope_code IN ('INTRADAY','SWING')),
    timeframe text NOT NULL,
    enabled boolean NOT NULL DEFAULT true,
    entry_policy jsonb NOT NULL CHECK(jsonb_typeof(entry_policy)='object'),
    exit_policy jsonb NOT NULL CHECK(jsonb_typeof(exit_policy)='object'),
    comparison_policy jsonb NOT NULL CHECK(jsonb_typeof(comparison_policy)='object'),
    pass_gates_unchanged boolean NOT NULL DEFAULT true CHECK(pass_gates_unchanged),
    live_allowed boolean NOT NULL DEFAULT false CHECK(NOT live_allowed),
    config_version text NOT NULL,
    updated_at timestamptz NOT NULL DEFAULT clock_timestamp(),
    PRIMARY KEY(scope_code,timeframe)
);

INSERT INTO analytics.research_entry_exit_contract_v1
 (scope_code,timeframe,entry_policy,exit_policy,comparison_policy,config_version)
VALUES
 ('INTRADAY','M5',
  '{"entry_policy_code":"META_ENTRY_V1","entry_trend_lookback":20,"entry_volatility_lookback":10,"entry_min_volatility_bps":2,"entry_max_volatility_bps":120,"entry_min_volume_ratio":1.0}',
  '{"exit_policy_code":["FIXED_HOLD","DYNAMIC_EXIT_V1"],"exit_max_holding_bars":20,"exit_atr_lookback":14,"exit_stop_atr":1.2,"exit_trail_atr":1.0,"exit_trend_lookback":5,"exit_volatility_lookback":10,"exit_volatility_risk_multiplier":2.0,"exit_minimum_bars":2}',
  '{"same_signals":true,"compare":["expectancy","profit_factor","drawdown","fold_stability"],"dynamic_must_outperform_fixed":true}',
  'DYNAMIC_EXIT_V1'),
 ('INTRADAY','M15',
  '{"entry_policy_code":"META_ENTRY_V1","entry_trend_lookback":16,"entry_volatility_lookback":8,"entry_min_volatility_bps":4,"entry_max_volatility_bps":180,"entry_min_volume_ratio":1.0}',
  '{"exit_policy_code":["FIXED_HOLD","DYNAMIC_EXIT_V1"],"exit_max_holding_bars":16,"exit_atr_lookback":14,"exit_stop_atr":1.2,"exit_trail_atr":1.0,"exit_trend_lookback":4,"exit_volatility_lookback":8,"exit_volatility_risk_multiplier":2.0,"exit_minimum_bars":2}',
  '{"same_signals":true,"compare":["expectancy","profit_factor","drawdown","fold_stability"],"dynamic_must_outperform_fixed":true}',
  'DYNAMIC_EXIT_V1'),
 ('SWING','H1',
  '{"entry_policy_code":"META_ENTRY_V1","entry_trend_lookback":40,"entry_volatility_lookback":20,"entry_min_volatility_bps":5,"entry_max_volatility_bps":300,"entry_min_volume_ratio":1.0}',
  '{"exit_policy_code":["FIXED_HOLD","DYNAMIC_EXIT_V1"],"exit_max_holding_bars":20,"exit_atr_lookback":14,"exit_stop_atr":1.5,"exit_trail_atr":1.2,"exit_trend_lookback":5,"exit_volatility_lookback":10,"exit_volatility_risk_multiplier":2.0,"exit_minimum_bars":2}',
  '{"same_signals":true,"compare":["expectancy","profit_factor","drawdown","fold_stability"],"dynamic_must_outperform_fixed":true}',
  'DYNAMIC_EXIT_V1'),
 ('SWING','H4',
  '{"entry_policy_code":"META_ENTRY_V1","entry_trend_lookback":20,"entry_volatility_lookback":10,"entry_min_volatility_bps":8,"entry_max_volatility_bps":500,"entry_min_volume_ratio":1.0}',
  '{"exit_policy_code":["FIXED_HOLD","DYNAMIC_EXIT_V1"],"exit_max_holding_bars":20,"exit_atr_lookback":10,"exit_stop_atr":1.5,"exit_trail_atr":1.2,"exit_trend_lookback":3,"exit_volatility_lookback":6,"exit_volatility_risk_multiplier":2.0,"exit_minimum_bars":2}',
  '{"same_signals":true,"compare":["expectancy","profit_factor","drawdown","fold_stability"],"dynamic_must_outperform_fixed":true}',
  'DYNAMIC_EXIT_V1'),
 ('SWING','D1',
  '{"entry_policy_code":"META_ENTRY_V1","entry_trend_lookback":10,"entry_volatility_lookback":8,"entry_min_volatility_bps":10,"entry_max_volatility_bps":800,"entry_min_volume_ratio":0.8}',
  '{"exit_policy_code":["FIXED_HOLD","DYNAMIC_EXIT_V1"],"exit_max_holding_bars":12,"exit_atr_lookback":10,"exit_stop_atr":1.8,"exit_trail_atr":1.5,"exit_trend_lookback":3,"exit_volatility_lookback":5,"exit_volatility_risk_multiplier":2.0,"exit_minimum_bars":2}',
  '{"same_signals":true,"compare":["expectancy","profit_factor","drawdown","fold_stability"],"dynamic_must_outperform_fixed":true}',
  'DYNAMIC_EXIT_V1')
ON CONFLICT(scope_code,timeframe) DO UPDATE SET
 enabled=true,entry_policy=excluded.entry_policy,exit_policy=excluded.exit_policy,
 comparison_policy=excluded.comparison_policy,pass_gates_unchanged=true,live_allowed=false,
 config_version=excluded.config_version,updated_at=clock_timestamp();

-- Intraday activation is deliberately limited to the two closest current
-- families, avoiding a full doubling of the hourly research load.
UPDATE analytics.edge_search_algorithm_registry_v1 r
SET parameter_grid=(
    SELECT jsonb_agg(item || entry_policy || jsonb_build_object('exit_policy_code',exit_code)
                     || (exit_policy - 'exit_policy_code') ORDER BY ordinal,exit_code)
    FROM jsonb_array_elements(r.parameter_grid) WITH ORDINALITY AS source(item,ordinal)
    CROSS JOIN analytics.research_entry_exit_contract_v1 c
    CROSS JOIN LATERAL jsonb_array_elements_text(c.exit_policy->'exit_policy_code') AS exits(exit_code)
    WHERE c.scope_code='INTRADAY' AND c.timeframe='M5'
), config_version='DYNAMIC_ENTRY_EXIT_V1',updated_at=clock_timestamp()
WHERE r.algorithm_code IN ('RSI','DONCHIAN_VOL_BREAKOUT')
  AND NOT EXISTS (SELECT 1 FROM jsonb_array_elements(r.parameter_grid) item WHERE item ? 'entry_policy_code');

UPDATE analytics.edge_search_scenario_v1
SET result_policy=result_policy || '{"entry_policy":"META_ENTRY_V1","exit_policy":"DYNAMIC_EXIT_V1","fixed_exit_baseline":true,"pass_gates":"unchanged"}'::jsonb,
    config_version='V4_DYNAMIC_ENTRY_EXIT',updated_at=clock_timestamp()
WHERE scenario_code='SWING_EDGE_SEARCH';

UPDATE analytics.system_job_schedule_v1
SET config_version='V4_DYNAMIC_ENTRY_EXIT',updated_at=clock_timestamp()
WHERE executor_code='SWING_EDGE_SEARCH_CYCLE_V1';

GRANT SELECT ON analytics.research_entry_exit_contract_v1 TO alex;

COMMIT;
