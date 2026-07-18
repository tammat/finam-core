BEGIN;
CREATE TABLE IF NOT EXISTS analytics.research_process_monitor_event_v1(
 event_id bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
 request_id text,process_id uuid,event_code text NOT NULL,detail text NOT NULL,
 created_at timestamptz NOT NULL DEFAULT clock_timestamp()
);
CREATE UNIQUE INDEX IF NOT EXISTS research_process_monitor_request_event_uq
 ON analytics.research_process_monitor_event_v1(request_id,event_code) WHERE request_id IS NOT NULL;
CREATE UNIQUE INDEX IF NOT EXISTS research_process_monitor_process_event_uq
 ON analytics.research_process_monitor_event_v1(process_id,event_code) WHERE process_id IS NOT NULL;
INSERT INTO analytics.system_job_schedule_v1(job_code,executor_code,enabled,timezone_code,weekdays,
 window_start,window_end,interval_minutes,timeout_seconds,priority,config_version)
VALUES('RESEARCH_PROCESS_MONITOR','RESEARCH_PROCESS_MONITOR_V1',true,'Europe/Moscow',
 '[0,1,2,3,4,5,6]'::jsonb,time '00:00',time '23:59:59',10,120,8,'V1')
ON CONFLICT(job_code) DO UPDATE SET executor_code=excluded.executor_code,enabled=true,
 interval_minutes=excluded.interval_minutes,timeout_seconds=excluded.timeout_seconds,
 priority=excluded.priority,config_version=excluded.config_version,updated_at=clock_timestamp();
INSERT INTO presentation.ui_resource_v1(resource_key,locale_code,caption,caption_short,caption_mobile,
 tooltip,resource_group,source_version) VALUES
 ('research.scout.column.status','ru','Статус','Статус','Стат.','Состояние действия оператора','research','RESEARCH_SCOUT_LOOP_V1'),
 ('research.scout.schedule.title','ru','Автозапуск','Автозапуск','Авто','Расписание автономной разведки','research','RESEARCH_SCOUT_LOOP_V1'),
 ('research.metric.scout_last_run','ru','Последний запуск','Последний','Было','Последний запуск разведки','research','RESEARCH_SCOUT_LOOP_V1'),
 ('research.metric.scout_next_run','ru','Следующий запуск','Следующий','Будет','Следующий автономный запуск','research','RESEARCH_SCOUT_LOOP_V1'),
 ('research.domain.scheduled','ru','Запланировано','По графику','План','Процесс будет запущен системой по графику','research','RESEARCH_SCOUT_LOOP_V1'),
 ('research.domain.scheduled.tooltip','ru','Система запустит автоматически','Автозапуск','Авто','Ручной запуск не требуется','research','RESEARCH_SCOUT_LOOP_V1'),
 ('research.universe.reason.autonomous_scout_selected','ru','Авторазведка','Разведка','Авто','Выбран автономной разведкой инструментов','research','RESEARCH_SCOUT_LOOP_V1')
 ,('research.scout.filter.active','ru','Активные','Активные','Актив.','Выбранные и резервные инструменты','research','RESEARCH_SCOUT_LOOP_V1')
 ,('research.scout.filter.selected','ru','Выбраны','Выбраны','Выбр.','Инструменты следующего исследования','research','RESEARCH_SCOUT_LOOP_V1')
 ,('research.scout.filter.reserve','ru','Резерв','Резерв','Рез.','Следующие контракты и резерв категории','research','RESEARCH_SCOUT_LOOP_V1')
 ,('research.scout.filter.backfill','ru','Сбор данных','Данные','Данные','Инструменты с недостаточной историей','research','RESEARCH_SCOUT_LOOP_V1')
 ,('research.scout.filter.excluded','ru','Исключены','Исключены','Нет','Инструменты, не прошедшие минимальный контракт','research','RESEARCH_SCOUT_LOOP_V1')
 ,('research.scout.filter.all','ru','Все','Все','Все','Полный журнал автономной разведки','research','RESEARCH_SCOUT_LOOP_V1')
ON CONFLICT(resource_key,locale_code) DO UPDATE SET caption=excluded.caption,caption_short=excluded.caption_short,
 caption_mobile=excluded.caption_mobile,tooltip=excluded.tooltip,source_version=excluded.source_version,updated_at=now();
GRANT SELECT,INSERT ON analytics.research_process_monitor_event_v1 TO alex;
COMMIT;
