BEGIN;

WITH definitions(algorithm_code,strategy_code,lookbacks,holds,thresholds,regimes) AS (
 VALUES
 ('MOMENTUM','MOMENTUM_CONTINUATION_V1',ARRAY[20,40,80],ARRAY[5,9],ARRAY[0.5,1.0,1.5],ARRAY['trend_up','trend_down','trend_up_expansion','trend_down_expansion']),
 ('VWAP','VWAP_REVERSION_V2',ARRAY[20,40,80],ARRAY[5,9],ARRAY[1.0,1.5,2.0],ARRAY['range_normal','range_compression','compression']),
 ('BOLLINGER','BOLLINGER_REVERSION_V1',ARRAY[20,40,80],ARRAY[5,9],ARRAY[1.5,2.0,2.5],ARRAY['range_normal','range_compression','compression']),
 ('RSI','RSI_MEAN_REVERSION_V1',ARRAY[14,21],ARRAY[5,9],ARRAY[20.0,25.0,30.0],ARRAY['range_normal','range_compression','compression']),
 ('BREAKOUT','VOLATILITY_BREAKOUT_V2',ARRAY[20,40,80],ARRAY[5,9],ARRAY[0.0],ARRAY['compression','trend_up_expansion','trend_down_expansion'])
), expanded AS (
 SELECT d.algorithm_code,d.strategy_code,d.regimes,
        jsonb_agg(jsonb_build_object('lookback',l,'hold',h,'threshold',t)
                  ORDER BY l,h,t) AS grid
 FROM definitions d
 CROSS JOIN LATERAL unnest(d.lookbacks) l
 CROSS JOIN LATERAL unnest(d.holds) h
 CROSS JOIN LATERAL unnest(d.thresholds) t
 GROUP BY d.algorithm_code,d.strategy_code,d.regimes
)
UPDATE analytics.edge_search_algorithm_registry_v1 a SET
 strategy_code=e.strategy_code,
 parameter_grid=e.grid,
 regime_policy=jsonb_build_object(
   'mode','contract_aware','allowed_regimes',to_jsonb(e.regimes),
   'minimum_confidence',0.60,'minimum_coverage',0.80),
 gate_policy='{
   "validation":{"min_trades":30,"min_profit_factor":1.05,"min_expectancy":0},
   "oos":{"min_trades":30,"min_profit_factor":1.10,"min_expectancy":0},
   "regime":{"min_folds_passed":2,"folds_total":3,"fold_min_trades":8,"fold_min_profit_factor":1.0,"fold_min_expectancy":0},
   "walkforward":{"min_trades":80,"min_profit_factor":1.15,"min_expectancy":0,"min_folds_passed":4,"folds_total":5,"fold_min_trades":12,"fold_min_profit_factor":1.0,"fold_min_expectancy":0,"final_holdout_required":true},
   "decision":"PASS_required"
 }'::jsonb,
 config_version='V2_DB_CONFIGURED',updated_at=clock_timestamp()
FROM expanded e WHERE a.algorithm_code=e.algorithm_code;

DO $$
BEGIN
 IF EXISTS (SELECT 1 FROM analytics.edge_search_algorithm_registry_v1 WHERE enabled AND jsonb_array_length(parameter_grid)=0) THEN
   RAISE EXCEPTION 'enabled edge-search algorithm has empty parameter grid';
 END IF;
END $$;

COMMIT;
