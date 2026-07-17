BEGIN;
WITH grids(algorithm_code,strategy_code,parameter_grid,allowed_regimes,template_algorithm) AS (
 SELECT 'EMA_TREND','EMA_TREND_FILTER_V1',
        jsonb_agg(jsonb_build_object('fast',fast,'slow',slow,'lookback',slow,'hold',hold,'threshold',threshold) ORDER BY fast,slow,hold,threshold),
        ARRAY['trend_up','trend_down','trend_up_expansion','trend_down_expansion'],'MOMENTUM'
 FROM unnest(ARRAY[10,20]) fast CROSS JOIN unnest(ARRAY[40,80]) slow
 CROSS JOIN unnest(ARRAY[9,18]) hold CROSS JOIN unnest(ARRAY[0.15,0.30]) threshold
 UNION ALL
 SELECT 'VOL_SCALED_MOMENTUM','VOLATILITY_SCALED_MOMENTUM_V1',
        jsonb_agg(jsonb_build_object('lookback',lookback,'vol_lookback',vol_lookback,'hold',hold,'threshold',threshold) ORDER BY lookback,vol_lookback,hold,threshold),
        ARRAY['trend_up','trend_down','trend_up_expansion','trend_down_expansion'],'MOMENTUM'
 FROM unnest(ARRAY[20,40,80]) lookback CROSS JOIN unnest(ARRAY[20,40]) vol_lookback
 CROSS JOIN unnest(ARRAY[5,9]) hold CROSS JOIN unnest(ARRAY[0.5,1.0]) threshold
 UNION ALL
 SELECT 'DONCHIAN_VOL_BREAKOUT','DONCHIAN_VOLATILITY_BREAKOUT_V1',
        jsonb_agg(jsonb_build_object('lookback',lookback,'hold',hold,'threshold',threshold) ORDER BY lookback,hold,threshold),
        ARRAY['compression','trend_up_expansion','trend_down_expansion'],'BREAKOUT'
 FROM unnest(ARRAY[20,40,80]) lookback CROSS JOIN unnest(ARRAY[9,18]) hold
 CROSS JOIN unnest(ARRAY[0.25,0.50]) threshold
)
INSERT INTO analytics.edge_search_algorithm_registry_v1
 (algorithm_code,strategy_code,enabled,parameter_grid,regime_policy,gate_policy,config_version)
SELECT g.algorithm_code,g.strategy_code,TRUE,g.parameter_grid,
       jsonb_build_object('mode','contract_aware','allowed_regimes',to_jsonb(g.allowed_regimes),
                          'minimum_confidence',0.60,'minimum_coverage',0.80),
       template.gate_policy,'V1_ORTHOGONAL_DB_CONFIGURED'
FROM grids g JOIN analytics.edge_search_algorithm_registry_v1 template
  ON template.algorithm_code=g.template_algorithm
ON CONFLICT (algorithm_code) DO UPDATE SET
 strategy_code=EXCLUDED.strategy_code,enabled=TRUE,parameter_grid=EXCLUDED.parameter_grid,
 regime_policy=EXCLUDED.regime_policy,gate_policy=EXCLUDED.gate_policy,
 config_version=EXCLUDED.config_version,updated_at=clock_timestamp();
COMMIT;
