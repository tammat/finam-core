BEGIN;

UPDATE analytics.system_job_schedule_v1
SET window_start=time '06:50',
    window_end=time '23:50',
    interval_minutes=30,
    timeout_seconds=1800,
    config_version='V3_FRESH_MICROSTRUCTURE_TRIGGER',
    updated_at=clock_timestamp()
WHERE job_code='SESSION_EXECUTION_EDGE_MICROSTRUCTURE_V2';

GRANT SELECT ON analytics.oos_remediation_candidate_v1 TO finam;
GRANT SELECT ON analytics.edge_oos_result_v1 TO finam;

INSERT INTO presentation.ui_resource_v1
    (resource_key,locale_code,caption,caption_short,caption_mobile,tooltip,icon,resource_group)
VALUES
('research.control.section.execution_microstructure.title','ru','Исполнение · Стакан','Стакан','Стакан','Новая независимая когорта: вход и выход подтверждены реальными bid/ask и глубиной стакана','','research'),
('research.control.section.execution_historical.title','ru','Исполнение · Свечи','Свечи','Свечи','Исторические результаты сохранены неизменными и не подтверждены биржевым стаканом','','research'),
('research.control.section.execution_microstructure.title','en','Execution · Order book','Order book','Book','Independent cohort with entry and exit matched to real bid/ask and depth','','research'),
('research.control.section.execution_historical.title','en','Execution · Bars','Bars','Bars','Immutable historical results without order-book confirmation','','research'),
('column.cohort_code','ru','Источник исполнения','Источник','Источник','Свечи — исторический расчёт; Стакан — независимое подтверждение bid/ask','','column'),
('column.cohort_code','en','Execution source','Source','Source','Bars are historical; Order book is independently verified bid/ask evidence','','column'),
('status.historical_bar_only','ru','Свечи','Свечи','Свечи','Исторические цены исполнения не подтверждены стаканом','','status'),
('status.microstructure_only','ru','Стакан','Стакан','Стакан','Вход и выход подтверждены реальными bid/ask и глубиной','','status'),
('status.historical_bar_only','en','Bars','Bars','Bars','Historical execution prices are not order-book verified','','status'),
('status.microstructure_only','en','Order book','Book','Book','Entry and exit are verified against real bid/ask and depth','','status')
ON CONFLICT (resource_key,locale_code) DO UPDATE SET
 caption=excluded.caption,caption_short=excluded.caption_short,
 caption_mobile=excluded.caption_mobile,tooltip=excluded.tooltip,
 icon=excluded.icon,resource_group=excluded.resource_group;

COMMIT;
