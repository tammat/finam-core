BEGIN;

ALTER TABLE analytics.instrument_scout_run_v1
 ADD COLUMN IF NOT EXISTS specification_pass integer NOT NULL DEFAULT 0,
 ADD COLUMN IF NOT EXISTS liquidity_pass integer NOT NULL DEFAULT 0,
 ADD COLUMN IF NOT EXISTS information_ranked integer NOT NULL DEFAULT 0,
 ADD COLUMN IF NOT EXISTS coarse_queued integer NOT NULL DEFAULT 0;

ALTER TABLE analytics.instrument_scout_result_v1
 ADD COLUMN IF NOT EXISTS provider_code text NOT NULL DEFAULT 'FINAM_MOEX',
 ADD COLUMN IF NOT EXISTS funnel_stage_code text NOT NULL DEFAULT 'DISCOVERED',
 ADD COLUMN IF NOT EXISTS history_ready boolean NOT NULL DEFAULT false,
 ADD COLUMN IF NOT EXISTS freshness_age_minutes numeric,
 ADD COLUMN IF NOT EXISTS avg_spread_bps numeric,
 ADD COLUMN IF NOT EXISTS spread_source text,
 ADD COLUMN IF NOT EXISTS median_volume numeric,
 ADD COLUMN IF NOT EXISTS capacity_rub numeric,
 ADD COLUMN IF NOT EXISTS max_abs_correlation numeric,
 ADD COLUMN IF NOT EXISTS regime_novelty_score numeric,
 ADD COLUMN IF NOT EXISTS information_value_score numeric,
 ADD COLUMN IF NOT EXISTS reserve_slot boolean NOT NULL DEFAULT false;

CREATE TABLE IF NOT EXISTS analytics.instrument_scout_funnel_event_v2(
 run_id uuid NOT NULL REFERENCES analytics.instrument_scout_run_v1(run_id) ON DELETE CASCADE,
 symbol text NOT NULL,
 stage_order integer NOT NULL CHECK(stage_order BETWEEN 1 AND 6),
 stage_code text NOT NULL CHECK(stage_code IN
  ('DISCOVERED','DATA_SPEC','LIQUIDITY','INFORMATION','CATEGORY_QUOTA','COARSE_SEARCH')),
 verdict_code text NOT NULL CHECK(verdict_code IN ('PASS','FAIL','RESERVE')),
 score numeric,
 reason_code text NOT NULL,
 evidence jsonb NOT NULL DEFAULT '{}'::jsonb,
 created_at timestamptz NOT NULL DEFAULT clock_timestamp(),
 PRIMARY KEY(run_id,symbol,stage_code)
);

CREATE INDEX IF NOT EXISTS instrument_scout_funnel_latest_v2_idx
 ON analytics.instrument_scout_funnel_event_v2(created_at DESC,stage_order,verdict_code);

UPDATE analytics.instrument_scout_policy_v1 SET policy=policy||
 '{"reserve_slots":3,"min_median_volume":1,"min_capacity_rub":50000,
   "max_spread_bps":35,"max_abs_correlation":0.92,"correlation_bars":1500,
   "information_weights":{"quality":35,"capacity":25,"diversification":25,"regime_novelty":15},
   "coarse_search_share":0.10}'::jsonb
WHERE policy_code='AUTONOMOUS_INSTRUMENT_SCOUT_V1';

INSERT INTO presentation.ui_resource_v1(resource_key,locale_code,caption,caption_short,caption_mobile,tooltip,resource_group,source_version) VALUES
 ('research.scout.funnel.title','ru','Воронка инструментов','Воронка','Воронка','Автономный отбор новых инструментов до грубого поиска','research','AUTONOMOUS_INSTRUMENT_FUNNEL_V2'),
 ('research.scout.funnel.discovered','ru','Обнаружено','Найдено','Найдено','Инструменты провайдера и биржи','research','AUTONOMOUS_INSTRUMENT_FUNNEL_V2'),
 ('research.scout.funnel.data_spec','ru','Данные и контракт','Допуск','Допуск','Свежие данные, история и спецификация','research','AUTONOMOUS_INSTRUMENT_FUNNEL_V2'),
 ('research.scout.funnel.liquidity','ru','Ликвидность','Ликвид.','Ликвид.','Приемлемые спред, объём и ёмкость','research','AUTONOMOUS_INSTRUMENT_FUNNEL_V2'),
 ('research.scout.funnel.information','ru','Ценность','Ценность','Ценность','Новый режим и низкая корреляция','research','AUTONOMOUS_INSTRUMENT_FUNNEL_V2'),
 ('research.scout.funnel.quota','ru','Квота','Квота','Квота','Категорийная квота или резерв','research','AUTONOMOUS_INSTRUMENT_FUNNEL_V2'),
 ('research.scout.funnel.coarse','ru','Грубый поиск','Поиск','Поиск','Передано в быстрый исследовательский отбор','research','AUTONOMOUS_INSTRUMENT_FUNNEL_V2'),
 ('research.scout.column.capacity','ru','Ёмкость','Ёмк.','Ёмк.','Оценочная доступная ёмкость в рублях','research','AUTONOMOUS_INSTRUMENT_FUNNEL_V2'),
 ('research.scout.column.correlation','ru','Корреляция','Корр.','Корр.','Максимальная абсолютная корреляция с выбранными рынками','research','AUTONOMOUS_INSTRUMENT_FUNNEL_V2')
ON CONFLICT(resource_key,locale_code) DO UPDATE SET caption=excluded.caption,caption_short=excluded.caption_short,
 caption_mobile=excluded.caption_mobile,tooltip=excluded.tooltip,source_version=excluded.source_version,updated_at=now();

GRANT SELECT,INSERT,UPDATE ON analytics.instrument_scout_funnel_event_v2 TO alex,finam;

COMMIT;
