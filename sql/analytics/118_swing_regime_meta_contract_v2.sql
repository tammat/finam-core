BEGIN;

CREATE TABLE IF NOT EXISTS analytics.swing_research_contract_v2 (
    family_code text PRIMARY KEY,
    title_ru text NOT NULL,
    engine_code text NOT NULL,
    enabled boolean NOT NULL DEFAULT true,
    priority integer NOT NULL CHECK(priority > 0),
    failure_triggers text[] NOT NULL,
    parameter_grid jsonb NOT NULL CHECK(jsonb_typeof(parameter_grid)='object'),
    pass_policy jsonb NOT NULL CHECK(jsonb_typeof(pass_policy)='object'),
    live_allowed boolean NOT NULL DEFAULT false CHECK(NOT live_allowed),
    config_version text NOT NULL,
    updated_at timestamptz NOT NULL DEFAULT clock_timestamp()
);

INSERT INTO analytics.swing_research_contract_v2
 (family_code,title_ru,engine_code,enabled,priority,failure_triggers,parameter_grid,pass_policy,config_version)
VALUES
 ('REGIME_MOMENTUM','Режимный импульс','SWING_REGIME_META_V1',true,10,
  ARRAY['NEGATIVE_COST_ADJUSTED_EXPECTANCY','WALKFORWARD_FOLDS_UNSTABLE','SELECTION_EDGE_FAILED','VALIDATION_EDGE_FAILED'],
  '{"lookback":[20,40,80],"threshold_bps":[20,40],"direction":["LONG","SHORT"],"trend_lookback":[40,80],"volatility_lookback":[10,20],"min_volatility_bps":[5],"max_volatility_bps":[300],"min_volume_ratio":[1.0,1.25]}'::jsonb,
  '{"selection_min_trades":20,"selection_min_pf":1.05,"validation_min_trades":15,"validation_min_pf":1.05,"validation_folds":2,"adjusted_p_max":0.05,"holdout":"locked","gates":"unchanged"}'::jsonb,
  'V2_DB_REGIME_META'),
 ('META_BREAKOUT','Фильтрованный пробой','SWING_REGIME_META_V1',true,20,
  ARRAY['NEGATIVE_COST_ADJUSTED_EXPECTANCY','WALKFORWARD_FOLDS_UNSTABLE','SELECTION_EDGE_FAILED','VALIDATION_EDGE_FAILED'],
  '{"lookback":[20,40,80],"confirmation_bars":[1,2],"trend_lookback":[40,80],"volatility_lookback":[10,20],"min_volatility_bps":[5],"max_volatility_bps":[300],"min_volume_ratio":[1.0,1.25]}'::jsonb,
  '{"selection_min_trades":20,"selection_min_pf":1.05,"validation_min_trades":15,"validation_min_pf":1.05,"validation_folds":2,"adjusted_p_max":0.05,"holdout":"locked","gates":"unchanged"}'::jsonb,
  'V2_DB_REGIME_META')
ON CONFLICT(family_code) DO UPDATE SET
 title_ru=excluded.title_ru,engine_code=excluded.engine_code,enabled=excluded.enabled,
 priority=excluded.priority,failure_triggers=excluded.failure_triggers,
 parameter_grid=excluded.parameter_grid,pass_policy=excluded.pass_policy,
 live_allowed=false,config_version=excluded.config_version,updated_at=clock_timestamp();

UPDATE analytics.edge_search_scenario_v1
SET title_ru='Режимный Swing и мета-фильтр',
    result_policy=result_policy || '{"contract_source":"analytics.swing_research_contract_v2","pass_gates":"unchanged","live_allowed":false}'::jsonb,
    config_version='V2_DB_REGIME_META',updated_at=clock_timestamp()
WHERE scenario_code='SWING_EDGE_SEARCH';

UPDATE analytics.system_job_schedule_v1
SET config_version='V2_DB_REGIME_META',updated_at=clock_timestamp()
WHERE executor_code='SWING_EDGE_SEARCH_CYCLE_V1';

GRANT SELECT ON analytics.swing_research_contract_v2 TO alex;

COMMIT;
