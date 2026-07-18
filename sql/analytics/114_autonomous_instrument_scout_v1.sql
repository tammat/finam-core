BEGIN;
CREATE TABLE IF NOT EXISTS analytics.instrument_scout_policy_v1(
 policy_code text PRIMARY KEY,active boolean NOT NULL DEFAULT false,policy jsonb NOT NULL,created_at timestamptz NOT NULL DEFAULT clock_timestamp()
);
CREATE UNIQUE INDEX IF NOT EXISTS instrument_scout_one_active_v1 ON analytics.instrument_scout_policy_v1(active) WHERE active;
INSERT INTO analytics.instrument_scout_policy_v1 VALUES('AUTONOMOUS_INSTRUMENT_SCOUT_V1',true,
 '{"max_selected":20,"min_bars":5000,"freshness_hours":72,"max_new_watch_symbols_per_run":4,
   "category_order":["OIL","GAS","METALS","FX","INDEX","EQUITY","OTHER"],
   "category_quotas":{"OIL":2,"GAS":2,"METALS":2,"FX":2,"INDEX":2,"EQUITY":8,"OTHER":2}}'::jsonb)
ON CONFLICT(policy_code) DO NOTHING;
CREATE TABLE IF NOT EXISTS analytics.instrument_scout_run_v1(
 run_id uuid PRIMARY KEY,status_code text NOT NULL,discovered integer NOT NULL DEFAULT 0,ready integer NOT NULL DEFAULT 0,
 selected integer NOT NULL DEFAULT 0,reserve integer NOT NULL DEFAULT 0,backfill integer NOT NULL DEFAULT 0,excluded integer NOT NULL DEFAULT 0,
 watch_added integer NOT NULL DEFAULT 0,error_code text,started_at timestamptz NOT NULL DEFAULT clock_timestamp(),finished_at timestamptz
);
CREATE TABLE IF NOT EXISTS analytics.instrument_scout_result_v1(
 run_id uuid NOT NULL REFERENCES analytics.instrument_scout_run_v1(run_id),symbol text NOT NULL,category_code text NOT NULL,
 asset_class text,market_code text,bars bigint NOT NULL,latest_ts timestamptz,market_score numeric NOT NULL DEFAULT 0,
 data_ready boolean NOT NULL,spec_ready boolean NOT NULL,liquidity_ready boolean NOT NULL,research_score numeric NOT NULL,
 category_rank integer NOT NULL,decision_code text NOT NULL,reason_codes jsonb NOT NULL,next_action_code text NOT NULL,
 source_version text NOT NULL DEFAULT 'AUTONOMOUS_INSTRUMENT_SCOUT_V1',created_at timestamptz NOT NULL DEFAULT clock_timestamp(),
 PRIMARY KEY(run_id,symbol)
);
CREATE INDEX IF NOT EXISTS instrument_scout_result_latest_v1 ON analytics.instrument_scout_result_v1(created_at DESC,decision_code,category_code);
CREATE TABLE IF NOT EXISTS analytics.instrument_scout_queue_v1(
 queue_id uuid PRIMARY KEY,run_id uuid NOT NULL REFERENCES analytics.instrument_scout_run_v1(run_id),symbol text NOT NULL,
 action_code text NOT NULL,status_code text NOT NULL DEFAULT 'PENDING',priority integer NOT NULL,evidence jsonb NOT NULL,
 created_at timestamptz NOT NULL DEFAULT clock_timestamp(),updated_at timestamptz NOT NULL DEFAULT clock_timestamp(),UNIQUE(run_id,symbol,action_code)
);
INSERT INTO analytics.system_job_schedule_v1(job_code,executor_code,enabled,timezone_code,weekdays,window_start,window_end,interval_minutes,timeout_seconds,priority,config_version)
VALUES('INSTRUMENT_SCOUT_DAILY','INSTRUMENT_SCOUT_V1',true,'Europe/Moscow','[0,1,2,3,4,5,6]'::jsonb,time '01:00',time '07:00',1440,900,19,'V1')
ON CONFLICT(job_code) DO UPDATE SET executor_code=excluded.executor_code,enabled=true,interval_minutes=excluded.interval_minutes,
 timeout_seconds=excluded.timeout_seconds,priority=excluded.priority,config_version=excluded.config_version,updated_at=clock_timestamp();
INSERT INTO presentation.ui_resource_v1(resource_key,locale_code,caption,caption_short,caption_mobile,tooltip,resource_group,source_version) VALUES
 ('research.tile.discovered','ru','Обнаружено','Найдено','Найдено','Инструменты последней разведки','research','AUTONOMOUS_INSTRUMENT_SCOUT_V1'),
 ('research.tile.new_instruments','ru','Новые','Новые','Новые','Новые инструменты, поставленные на сбор данных','research','AUTONOMOUS_INSTRUMENT_SCOUT_V1'),
 ('research.scout.title','ru','Разведка инструментов','Разведка','Разведка','Автономный поиск и отбор новых рынков','research','AUTONOMOUS_INSTRUMENT_SCOUT_V1'),
 ('research.scout.column.decision','ru','Решение','Решение','Реш.','Решение автономного отбора','research','AUTONOMOUS_INSTRUMENT_SCOUT_V1'),
 ('research.scout.column.symbol','ru','Инструмент','Инструмент','Инстр.','Торговый символ','research','AUTONOMOUS_INSTRUMENT_SCOUT_V1'),
 ('research.scout.column.category','ru','Категория','Категория','Кат.','Категория рынка','research','AUTONOMOUS_INSTRUMENT_SCOUT_V1'),
 ('research.scout.column.score','ru','Оценка','Оценка','Балл','Исследовательская ценность','research','AUTONOMOUS_INSTRUMENT_SCOUT_V1'),
 ('research.scout.column.bars','ru','Бары','Бары','Бары','Доступная история','research','AUTONOMOUS_INSTRUMENT_SCOUT_V1'),
 ('research.scout.column.reason','ru','Причина','Причина','Прич.','Причина решения','research','AUTONOMOUS_INSTRUMENT_SCOUT_V1'),
 ('research.scout.column.action','ru','Далее','Далее','Далее','Следующее системное действие','research','AUTONOMOUS_INSTRUMENT_SCOUT_V1'),
 ('research.scout.decision.selected','ru','Выбран','Выбран','Да','Включён в следующий исследовательский цикл','research','AUTONOMOUS_INSTRUMENT_SCOUT_V1'),
 ('research.scout.decision.reserve','ru','Резерв','Резерв','Рез.','Готов, но не вошёл в квоту','research','AUTONOMOUS_INSTRUMENT_SCOUT_V1'),
 ('research.scout.decision.backfill','ru','Сбор данных','Данные','Данные','Требуется накопление истории','research','AUTONOMOUS_INSTRUMENT_SCOUT_V1'),
 ('research.scout.decision.excluded','ru','Исключён','Исключён','Нет','Не соответствует минимальному контракту','research','AUTONOMOUS_INSTRUMENT_SCOUT_V1')
ON CONFLICT(resource_key,locale_code) DO UPDATE SET caption=excluded.caption,caption_short=excluded.caption_short,
 caption_mobile=excluded.caption_mobile,tooltip=excluded.tooltip,source_version=excluded.source_version,updated_at=now();
GRANT SELECT,INSERT,UPDATE ON analytics.instrument_scout_policy_v1,analytics.instrument_scout_run_v1,
 analytics.instrument_scout_result_v1,analytics.instrument_scout_queue_v1 TO alex;
COMMIT;
