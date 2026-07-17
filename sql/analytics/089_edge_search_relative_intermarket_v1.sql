BEGIN;

WITH canonical AS (
  SELECT gate_policy FROM analytics.edge_search_algorithm_registry_v1
  WHERE algorithm_code='DONCHIAN_VOL_BREAKOUT'
)
INSERT INTO analytics.edge_search_algorithm_registry_v1
(algorithm_code,strategy_code,enabled,parameter_grid,regime_policy,gate_policy,config_version,updated_at)
SELECT v.algorithm_code,v.strategy_code,true,v.parameter_grid,v.regime_policy,
       canonical.gate_policy,'V1_RELATIVE_INTERMARKET_STRICT_GATES',clock_timestamp()
FROM canonical CROSS JOIN (VALUES
 ('DONCHIAN_TREND_EXPANSION','DONCHIAN_VOLATILITY_BREAKOUT_V1',
  '[{"lookback":20,"hold":3,"threshold":0.10},{"lookback":20,"hold":5,"threshold":0.20},{"lookback":40,"hold":3,"threshold":0.10},{"lookback":40,"hold":5,"threshold":0.20},{"lookback":40,"hold":5,"threshold":0.30},{"lookback":40,"hold":9,"threshold":0.20},{"lookback":80,"hold":3,"threshold":0.10},{"lookback":80,"hold":5,"threshold":0.20},{"lookback":80,"hold":5,"threshold":0.30}]'::jsonb,
  '{"mode":"contract_aware","allowed_regimes":["trend_up_expansion","trend_down_expansion"],"minimum_coverage":0.80,"minimum_confidence":0.60}'::jsonb),
 ('RELATIVE_STRENGTH','RELATIVE_STRENGTH_V1',
  '[{"lookback":20,"hold":3,"threshold":0.25},{"lookback":20,"hold":5,"threshold":0.50},{"lookback":40,"hold":3,"threshold":0.25},{"lookback":40,"hold":5,"threshold":0.50},{"lookback":40,"hold":9,"threshold":0.75},{"lookback":80,"hold":3,"threshold":0.25},{"lookback":80,"hold":5,"threshold":0.50},{"lookback":80,"hold":9,"threshold":0.75}]'::jsonb,
  '{"mode":"contract_aware","reference_symbol":"IMOEX2","target_symbols":["SBER@MISX","SBERP@MISX","LKOH@MISX","GAZP@MISX","NVTK@MISX","PLZL@MISX","T@MISX"],"allowed_regimes":["trend_up","trend_down","trend_up_expansion","trend_down_expansion"],"minimum_coverage":0.80,"minimum_confidence":0.60}'::jsonb),
 ('INTERMARKET_SBER_SPREAD','INTERMARKET_SPREAD_REVERSION_V1',
  '[{"lookback":20,"hold":3,"threshold":1.5},{"lookback":20,"hold":5,"threshold":2.0},{"lookback":40,"hold":3,"threshold":1.5},{"lookback":40,"hold":5,"threshold":2.0},{"lookback":80,"hold":3,"threshold":1.5},{"lookback":80,"hold":5,"threshold":2.0}]'::jsonb,
  '{"mode":"contract_aware","reference_symbol":"SBERP@MISX","target_symbols":["SBER@MISX"],"allowed_regimes":["range_normal","range_compression","compression"],"minimum_coverage":0.80,"minimum_confidence":0.60}'::jsonb)
) AS v(algorithm_code,strategy_code,parameter_grid,regime_policy)
ON CONFLICT(algorithm_code) DO UPDATE SET
 strategy_code=EXCLUDED.strategy_code,enabled=true,parameter_grid=EXCLUDED.parameter_grid,
 regime_policy=EXCLUDED.regime_policy,gate_policy=EXCLUDED.gate_policy,
 config_version=EXCLUDED.config_version,updated_at=clock_timestamp();

INSERT INTO presentation.ui_resource_v1
(resource_key,locale_code,caption,caption_short,caption_mobile,tooltip,icon,resource_group) VALUES
('research.domain.donchian_trend_expansion','ru','Дончиан по тренду','Дончиан','Донч.','Пробой Дончиана только в режимах расширения тренда','','research'),
('research.domain.relative_strength','ru','Относительная сила','Отн. сила','Сила','Доходность инструмента относительно индекса IMOEX2','','research'),
('research.domain.intermarket_sber_spread','ru','Спред SBER/SBERP','Спред','Спред','Возврат отношения SBER к SBERP к среднему','','research')
ON CONFLICT(resource_key,locale_code) DO UPDATE SET
caption=EXCLUDED.caption,caption_short=EXCLUDED.caption_short,caption_mobile=EXCLUDED.caption_mobile,
tooltip=EXCLUDED.tooltip,icon=EXCLUDED.icon,resource_group=EXCLUDED.resource_group;

COMMIT;
