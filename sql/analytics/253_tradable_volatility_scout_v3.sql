BEGIN;

ALTER TABLE analytics.instrument_scout_run_v1
 ADD COLUMN IF NOT EXISTS volatility_pass integer NOT NULL DEFAULT 0;

ALTER TABLE analytics.instrument_scout_result_v1
 ADD COLUMN IF NOT EXISTS atr_pct numeric,
 ADD COLUMN IF NOT EXISTS atr_percentile numeric,
 ADD COLUMN IF NOT EXISTS rv20 numeric,
 ADD COLUMN IF NOT EXISTS rv60 numeric,
 ADD COLUMN IF NOT EXISTS volatility_acceleration numeric,
 ADD COLUMN IF NOT EXISTS volume_zscore numeric,
 ADD COLUMN IF NOT EXISTS directional_efficiency numeric,
 ADD COLUMN IF NOT EXISTS volatility_persistence numeric,
 ADD COLUMN IF NOT EXISTS zero_volume_share numeric,
 ADD COLUMN IF NOT EXISTS spread_atr_ratio numeric,
 ADD COLUMN IF NOT EXISTS tradable_volatility_score numeric,
 ADD COLUMN IF NOT EXISTS candidate_stage_code text NOT NULL DEFAULT 'OBSERVATION';

ALTER TABLE analytics.instrument_scout_funnel_event_v2
 DROP CONSTRAINT IF EXISTS instrument_scout_funnel_event_v2_stage_order_check,
 DROP CONSTRAINT IF EXISTS instrument_scout_funnel_event_v2_stage_code_check;
ALTER TABLE analytics.instrument_scout_funnel_event_v2
 ADD CONSTRAINT instrument_scout_funnel_event_v2_stage_order_check
   CHECK(stage_order BETWEEN 1 AND 7),
 ADD CONSTRAINT instrument_scout_funnel_event_v2_stage_code_check
   CHECK(stage_code IN ('DISCOVERED','DATA_SPEC','LIQUIDITY','VOLATILITY',
                        'INFORMATION','CATEGORY_QUOTA','COARSE_SEARCH'));

UPDATE analytics.instrument_scout_policy_v1
SET policy=policy||'{
  "max_selected":10,
  "category_quotas":{"OIL":1,"GAS":1,"METALS":1,"FX":1,"INDEX":1,"EQUITY":5,"OTHER":0},
  "min_atr_pct":0.05,
  "max_zero_volume_share":0.15,
  "max_spread_atr_ratio":0.25,
  "min_tradable_volatility_score":45
}'::jsonb
WHERE policy_code='AUTONOMOUS_INSTRUMENT_SCOUT_V1';

INSERT INTO presentation.ui_resource_v1(
 resource_key,locale_code,caption,caption_short,caption_mobile,tooltip,resource_group,source_version)
VALUES
 ('research.scout.funnel.volatility','ru','Торгуемая волатильность','Волатильность','Волат.','ATR, ускорение, объём и стоимость исполнения','research','TRADABLE_VOLATILITY_SCOUT_V3'),
 ('research.scout.column.atr_pct','ru','ATR, %','ATR, %','ATR','Средний истинный диапазон относительно цены','research','TRADABLE_VOLATILITY_SCOUT_V3'),
 ('research.scout.column.volatility_score','ru','Оценка волатильности','Vol score','Vol','Волатильность после штрафов за спред и пустые свечи','research','TRADABLE_VOLATILITY_SCOUT_V3'),
 ('research.scout.stage.observation','ru','Наблюдение','Наблюдение','Набл.','Инструмент не допускается выше наблюдения','research','TRADABLE_VOLATILITY_SCOUT_V3'),
 ('research.scout.stage.shadow','ru','Готов к Shadow','Shadow','Shadow','Допущен только к исследовательской Shadow-проверке','research','TRADABLE_VOLATILITY_SCOUT_V3')
ON CONFLICT(resource_key,locale_code) DO UPDATE SET
 caption=excluded.caption,caption_short=excluded.caption_short,
 caption_mobile=excluded.caption_mobile,tooltip=excluded.tooltip,
 source_version=excluded.source_version,updated_at=now();

GRANT SELECT,INSERT,UPDATE ON analytics.instrument_scout_result_v1,
 analytics.instrument_scout_run_v1,analytics.instrument_scout_funnel_event_v2 TO alex;

COMMIT;
