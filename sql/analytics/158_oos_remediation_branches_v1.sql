BEGIN;

CREATE TABLE IF NOT EXISTS analytics.oos_remediation_process_v1(
    process_id uuid PRIMARY KEY,
    parent_scenario_run_id uuid NOT NULL,
    parent_search_run_id uuid NOT NULL,
    status_code text NOT NULL CHECK(status_code IN ('GENERATING','MONITORING','COMPLETE','FAILED')),
    current_step_code text NOT NULL,
    progress_pct numeric(6,2) NOT NULL DEFAULT 0 CHECK(progress_pct BETWEEN 0 AND 100),
    source_failures integer NOT NULL DEFAULT 0,
    error_code text,
    config_version text NOT NULL,
    started_at timestamptz NOT NULL DEFAULT clock_timestamp(),
    finished_at timestamptz,
    updated_at timestamptz NOT NULL DEFAULT clock_timestamp(),
    UNIQUE(parent_search_run_id,config_version)
);

CREATE TABLE IF NOT EXISTS analytics.oos_remediation_candidate_v1(
    candidate_id uuid PRIMARY KEY,
    process_id uuid NOT NULL REFERENCES analytics.oos_remediation_process_v1(process_id),
    branch_code text NOT NULL CHECK(branch_code IN ('COST_REMEDIATION','SAMPLE_EXPANSION')),
    parent_result_id uuid NOT NULL,
    adaptive_scenario_id uuid REFERENCES analytics.edge_search_adaptive_scenario_v1(adaptive_scenario_id),
    algorithm_code text NOT NULL,
    strategy_code text NOT NULL,
    symbol text NOT NULL,
    parameter_json jsonb NOT NULL CHECK(jsonb_typeof(parameter_json)='object'),
    fingerprint text NOT NULL,
    status_code text NOT NULL CHECK(status_code IN (
      'GENERATED','PRUNED_DUPLICATE','PRUNED_BUDGET','WAITING_FUTURE_DATA',
      'QUEUED','EVALUATED_FAIL','OOS_PASS'
    )),
    reason_code text NOT NULL,
    generated_at timestamptz NOT NULL DEFAULT clock_timestamp(),
    evaluated_at timestamptz,
    updated_at timestamptz NOT NULL DEFAULT clock_timestamp(),
    UNIQUE(process_id,branch_code,fingerprint)
);
CREATE INDEX IF NOT EXISTS oos_remediation_candidate_process_idx
ON analytics.oos_remediation_candidate_v1(process_id,branch_code,status_code);
CREATE INDEX IF NOT EXISTS oos_remediation_candidate_fingerprint_idx
ON analytics.oos_remediation_candidate_v1(fingerprint);

CREATE OR REPLACE VIEW analytics.oos_remediation_branch_summary_v1 AS
WITH latest AS (
  SELECT process_id FROM analytics.oos_remediation_process_v1
  ORDER BY started_at DESC LIMIT 1
), branches(branch_code) AS (
  VALUES ('COST_REMEDIATION'::text),('SAMPLE_EXPANSION'::text)
)
SELECT p.process_id,b.branch_code,p.status_code AS process_status,p.current_step_code,
       p.progress_pct,p.started_at,p.updated_at,
       count(DISTINCT c.parent_result_id) AS source_failures,
       count(c.candidate_id) AS created_variants,
       count(c.candidate_id) FILTER(WHERE c.status_code LIKE 'PRUNED_%') AS pruned_variants,
       count(c.candidate_id) FILTER(WHERE c.status_code IN ('WAITING_FUTURE_DATA','QUEUED')) AS queued_variants,
       count(c.candidate_id) FILTER(WHERE c.status_code IN ('EVALUATED_FAIL','OOS_PASS')) AS evaluated_variants,
       count(c.candidate_id) FILTER(WHERE c.status_code='OOS_PASS') AS oos_pass
FROM latest l JOIN analytics.oos_remediation_process_v1 p USING(process_id)
CROSS JOIN branches b
LEFT JOIN analytics.oos_remediation_candidate_v1 c
  ON c.process_id=p.process_id AND c.branch_code=b.branch_code
GROUP BY p.process_id,b.branch_code,p.status_code,p.current_step_code,p.progress_pct,p.started_at,p.updated_at;

INSERT INTO analytics.system_job_schedule_v1(
 job_code,executor_code,enabled,timezone_code,weekdays,window_start,window_end,
 interval_minutes,timeout_seconds,priority,config_version)
VALUES('OOS_REMEDIATION_BRANCH_GENERATOR','OOS_REMEDIATION_BRANCH_GENERATOR_V1',true,
 'Europe/Moscow','[0,1,2,3,4,5,6]'::jsonb,time '00:00',time '23:59',15,120,34,
 'OOS_REMEDIATION_BRANCHES_V1')
ON CONFLICT(job_code) DO UPDATE SET executor_code=excluded.executor_code,enabled=true,
 timezone_code=excluded.timezone_code,weekdays=excluded.weekdays,
 window_start=excluded.window_start,window_end=excluded.window_end,
 interval_minutes=excluded.interval_minutes,timeout_seconds=excluded.timeout_seconds,
 priority=excluded.priority,config_version=excluded.config_version,updated_at=clock_timestamp();

INSERT INTO presentation.ui_resource_v1
(resource_key,locale_code,caption,caption_short,caption_mobile,tooltip,icon,resource_group)
VALUES
('research.remediation.title','ru','Ветки восстановления OOS','Ветки OOS','Ветки','Автономные ветки создают новые варианты по конкретным причинам отказа, не ослабляя критерии PASS','','research'),
('research.remediation.column.branch','ru','Ветка','Ветка','Ветка','Тип автоматического исправления','','research'),
('research.remediation.column.sources','ru','Причины','Причины','Прич.','Количество исходных отказов, использованных генератором','','research'),
('research.remediation.column.created','ru','Создано','Создано','Созд.','Все сгенерированные варианты до отсева','','research'),
('research.remediation.column.pruned','ru','Отсеяно','Отсеяно','Отс.','Дубликаты и варианты сверх безопасного вычислительного бюджета','','research'),
('research.remediation.column.queued','ru','В работе','В работе','Раб.','Ожидают будущих данных или следующего системного цикла','','research'),
('research.remediation.column.evaluated','ru','Проверено','Проверено','Пров.','Варианты с завершённым OOS-результатом','','research'),
('research.remediation.column.pass','ru','OOS PASS','PASS','PASS','Варианты, прошедшие неизменённые критерии OOS PASS','','research'),
('research.remediation.column.status','ru','Статус','Статус','Стат.','Текущее состояние DB-процесса','','research'),
('research.remediation.column.action','ru','Действие','Действие','Действ.','Двойной клик открывает системное действие','','research'),
('research.remediation.branch.cost_remediation','ru','Издержки','Издержки','Изд.','Усиление входа и сокращение удержания при неизменной модели комиссий и проскальзывания','','research'),
('research.remediation.branch.sample_expansion','ru','Выборка','Выборка','Выб.','Расширение числа независимых сделок без ослабления PASS','','research'),
('research.remediation.action','ru','Продолжить','Продолжить','Далее','Поставить DB-driven исследовательский цикл в очередь','','research'),
('research.domain.monitoring','ru','В работе','В работе','Работа','Система ждёт независимую OOS-проверку созданных вариантов','','research'),
('research.domain.monitoring.tooltip','ru','Автономный цикл продолжится по расписанию','В работе','Работа','Ручной запуск алгоритма не требуется','','research'),
('column.cohort.code','ru','Когорта','Когорта','Ког.','Код независимой исследовательской когорты','','control_center'),
('research.remediation.title','en','OOS remediation branches','OOS branches','Branches','Autonomous fail-driven branches with unchanged PASS gates','','research'),
('research.remediation.column.branch','en','Branch','Branch','Branch','Automatic remediation branch','','research'),
('research.remediation.column.sources','en','Sources','Sources','Src.','Source failures used by the generator','','research'),
('research.remediation.column.created','en','Created','Created','New','Generated variants before pruning','','research'),
('research.remediation.column.pruned','en','Pruned','Pruned','Cut','Duplicates and variants outside the compute budget','','research'),
('research.remediation.column.queued','en','In work','In work','Work','Waiting for future data or the next system cycle','','research'),
('research.remediation.column.evaluated','en','Evaluated','Evaluated','Eval.','Variants with a completed OOS result','','research'),
('research.remediation.column.pass','en','OOS PASS','PASS','PASS','Variants passing unchanged OOS gates','','research'),
('research.remediation.column.status','en','Status','Status','Status','Current DB process state','','research'),
('research.remediation.column.action','en','Action','Action','Action','Double-click opens the system action','','research'),
('research.remediation.branch.cost_remediation','en','Costs','Costs','Costs','Stronger entries and shorter holds with unchanged costs','','research'),
('research.remediation.branch.sample_expansion','en','Sample','Sample','Sample','More independent trades without weakening PASS','','research'),
('research.remediation.action','en','Continue','Continue','Next','Queue the DB-driven research cycle','','research')
,('research.domain.monitoring','en','In progress','In progress','Running','The system is waiting for independent OOS evaluation','','research')
,('research.domain.monitoring.tooltip','en','The autonomous cycle continues on schedule','In progress','Running','No manual algorithm run is required','','research')
,('column.cohort.code','en','Cohort','Cohort','Cohort','Independent research cohort code','','control_center')
ON CONFLICT(resource_key,locale_code) DO UPDATE SET caption=excluded.caption,
 caption_short=excluded.caption_short,caption_mobile=excluded.caption_mobile,
 tooltip=excluded.tooltip,icon=excluded.icon,resource_group=excluded.resource_group;

GRANT SELECT,INSERT,UPDATE ON analytics.oos_remediation_process_v1 TO alex,finam;
GRANT SELECT,INSERT,UPDATE ON analytics.oos_remediation_candidate_v1 TO alex,finam;
GRANT SELECT ON analytics.oos_remediation_branch_summary_v1 TO alex,finam;

COMMIT;
