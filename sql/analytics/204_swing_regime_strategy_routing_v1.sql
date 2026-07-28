BEGIN;

CREATE TABLE IF NOT EXISTS analytics.swing_regime_strategy_routing_v1 (
    market_scope text NOT NULL CHECK (market_scope IN ('EQUITY','FUTURES')),
    symbol_pattern text NOT NULL,
    timeframe text NOT NULL CHECK (timeframe IN ('H1','H4','D1')),
    regime_code text NOT NULL CHECK (regime_code IN ('RANGE','TREND_UP','TREND_DOWN')),
    strategy_family text NOT NULL REFERENCES analytics.swing_research_contract_v2(family_code),
    allowed_side text NOT NULL CHECK (allowed_side IN ('LONG','SHORT','BOTH')),
    priority integer NOT NULL CHECK (priority > 0),
    enabled boolean NOT NULL DEFAULT true,
    pass_gates_unchanged boolean NOT NULL DEFAULT true CHECK (pass_gates_unchanged),
    live_allowed boolean NOT NULL DEFAULT false CHECK (NOT live_allowed),
    config_version text NOT NULL,
    updated_at timestamptz NOT NULL DEFAULT clock_timestamp(),
    PRIMARY KEY (market_scope,timeframe,regime_code)
);

INSERT INTO analytics.swing_research_contract_v2
 (family_code,title_ru,engine_code,enabled,priority,failure_triggers,parameter_grid,pass_policy,config_version)
VALUES
 ('SWING_MEAN_REVERSION','Swing: возврат к среднему','SWING_REGIME_ROUTER_V1',true,15,
  ARRAY['NEGATIVE_COST_ADJUSTED_EXPECTANCY','SELECTION_EDGE_FAILED','VALIDATION_EDGE_FAILED'],
  '{"lookback":[20,40],"entry_zscore":[1.0,1.5,2.0],"trend_lookback":[20,40],"volatility_lookback":[10,20],"min_volatility_bps":[0],"max_volatility_bps":[300],"min_volume_ratio":[0.8,1.0]}'::jsonb,
  '{"selection_min_trades":20,"selection_min_pf":1.05,"validation_min_trades":15,"validation_min_pf":1.05,"validation_folds":2,"adjusted_p_max":0.05,"holdout":"locked","gates":"unchanged"}'::jsonb,
  'V1_DB_SWING_REGIME_ROUTER')
ON CONFLICT(family_code) DO UPDATE SET
 title_ru=excluded.title_ru,engine_code=excluded.engine_code,enabled=excluded.enabled,
 priority=excluded.priority,failure_triggers=excluded.failure_triggers,
 parameter_grid=excluded.parameter_grid,pass_policy=excluded.pass_policy,
 live_allowed=false,config_version=excluded.config_version,updated_at=clock_timestamp();

INSERT INTO analytics.swing_regime_strategy_routing_v1
 (market_scope,symbol_pattern,timeframe,regime_code,strategy_family,allowed_side,priority,config_version)
SELECT market_scope,symbol_pattern,timeframe,regime_code,strategy_family,allowed_side,priority,
       'V1_DB_SWING_REGIME_ROUTER'
FROM (VALUES
 ('EQUITY','%@MISX','RANGE','SWING_MEAN_REVERSION','BOTH',10),
 ('EQUITY','%@MISX','TREND_UP','META_BREAKOUT','LONG',20),
 ('EQUITY','%@MISX','TREND_DOWN','META_BREAKOUT','SHORT',20),
 ('FUTURES','%@RTSX','RANGE','SWING_MEAN_REVERSION','BOTH',10),
 ('FUTURES','%@RTSX','TREND_UP','META_BREAKOUT','LONG',20),
 ('FUTURES','%@RTSX','TREND_DOWN','META_BREAKOUT','SHORT',20)
) AS routes(market_scope,symbol_pattern,regime_code,strategy_family,allowed_side,priority)
CROSS JOIN (VALUES ('H1'),('H4'),('D1')) AS timeframes(timeframe)
ON CONFLICT(market_scope,timeframe,regime_code) DO UPDATE SET
 symbol_pattern=excluded.symbol_pattern,strategy_family=excluded.strategy_family,
 allowed_side=excluded.allowed_side,priority=excluded.priority,enabled=true,
 pass_gates_unchanged=true,live_allowed=false,config_version=excluded.config_version,
 updated_at=clock_timestamp();

UPDATE analytics.edge_search_scenario_v1
SET title_ru='Режимный Swing: H1, H4 и D1',
    result_policy=result_policy || '{
      "routing_source":"analytics.swing_regime_strategy_routing_v1",
      "intraday_mixed":false,
      "unknown_regime_allowed":false,
      "pass_gates":"unchanged",
      "live_allowed":false
    }'::jsonb,
    config_version='V5_DB_SWING_REGIME_ROUTER',
    updated_at=clock_timestamp()
WHERE scenario_code='SWING_EDGE_SEARCH';

UPDATE analytics.system_job_schedule_v1
SET config_version='V5_DB_SWING_REGIME_ROUTER',updated_at=clock_timestamp()
WHERE executor_code='SWING_EDGE_SEARCH_CYCLE_V1';

GRANT SELECT ON analytics.swing_regime_strategy_routing_v1 TO alex;

COMMIT;
