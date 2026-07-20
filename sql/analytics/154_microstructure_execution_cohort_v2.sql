BEGIN;

ALTER TABLE analytics.execution_edge_result_v1
    ADD COLUMN IF NOT EXISTS cohort_code TEXT NOT NULL DEFAULT 'HISTORICAL_BAR_ONLY',
    ADD COLUMN IF NOT EXISTS eligible_oos_trades INTEGER NOT NULL DEFAULT 0,
    ADD COLUMN IF NOT EXISTS microstructure_matched_trades INTEGER NOT NULL DEFAULT 0,
    ADD COLUMN IF NOT EXISTS microstructure_coverage_ratio NUMERIC NOT NULL DEFAULT 0,
    ADD COLUMN IF NOT EXISTS microstructure_start TIMESTAMPTZ,
    ADD COLUMN IF NOT EXISTS microstructure_end TIMESTAMPTZ;

UPDATE analytics.execution_edge_result_v1
SET cohort_code='HISTORICAL_BAR_ONLY',
    eligible_oos_trades=oos_trades,
    microstructure_matched_trades=0,
    microstructure_coverage_ratio=0
WHERE cohort_code='HISTORICAL_BAR_ONLY';

ALTER TABLE analytics.execution_edge_result_v1
    DROP CONSTRAINT IF EXISTS execution_edge_result_v1_market_data_quality_check;

ALTER TABLE analytics.execution_edge_result_v1
    ADD CONSTRAINT execution_edge_result_v1_market_data_quality_check
        CHECK (market_data_quality IN ('BAR_ONLY','QUOTE_VERIFIED','MICROSTRUCTURE_VERIFIED')),
    ADD CONSTRAINT execution_edge_result_v1_cohort_code_check
        CHECK (cohort_code IN ('HISTORICAL_BAR_ONLY','MICROSTRUCTURE_ONLY')),
    ADD CONSTRAINT execution_edge_result_v1_microstructure_counts_check
        CHECK (eligible_oos_trades >= 0
           AND microstructure_matched_trades >= 0
           AND microstructure_matched_trades <= eligible_oos_trades),
    ADD CONSTRAINT execution_edge_result_v1_microstructure_coverage_check
        CHECK (microstructure_coverage_ratio BETWEEN 0 AND 1);

CREATE INDEX IF NOT EXISTS execution_edge_result_v1_cohort_latest_idx
    ON analytics.execution_edge_result_v1(cohort_code,created_at DESC);

INSERT INTO presentation.ui_resource_v1
(resource_key,locale_code,caption,caption_short,caption_mobile,tooltip,icon,resource_group)
VALUES
('research.domain.microstructure_verified','ru','Исполнение подтверждено стаканом','Стакан','Стакан','Вход и выход сделки сопоставлены с реальными bid/ask, глубиной и биржевой меткой времени','','research'),
('research.domain.historical_bar_only','ru','Исторический расчёт только по свечам','Свечи','Свечи','Старый неизменяемый результат: цены исполнения не подтверждены микроструктурой рынка','','research'),
('research.domain.microstructure_only','ru','Независимая микроструктурная когорта','Стакан','Стакан','В расчёт включены только сделки с подтверждёнными котировками на входе и выходе','','research'),
('research.domain.microstructure_data_unverified','ru','Недостаточно подтверждённых котировок','Мало данных','Мало','Доля сделок с реальными bid/ask ниже строгого порога 80%','','research'),
('column.best_bid','ru','Лучшая цена покупки','Bid','Bid','Реальная лучшая цена покупки из биржевого стакана','','column'),
('column.best_ask','ru','Лучшая цена продажи','Ask','Ask','Реальная лучшая цена продажи из биржевого стакана','','column'),
('column.bid_depth','ru','Глубина покупок','Глуб. bid','Bid','Суммарная доступная глубина покупки','','column'),
('column.ask_depth','ru','Глубина продаж','Глуб. ask','Ask','Суммарная доступная глубина продажи','','column'),
('column.exchange_ts','ru','Биржевое время','Время биржи','Время','Метка времени, полученная из биржевого источника','','column'),
('column.microstructure_coverage_pct','ru','Покрытие стаканом, %','Покрытие','Покр.','Доля сделок, у которых подтверждены котировки входа и выхода','','column'),
('column.microstructure_matched_trades','ru','Подтверждённые сделки','Подтв.','Подтв.','Сделки с реальными bid/ask на входе и выходе','','column'),
('column.eligible_oos_trades','ru','Доступные OOS-сделки','OOS всего','OOS','Все сделки до проверки микроструктуры','','column'),
('column.microstructure_start','ru','Начало подтверждения','Начало','Нач.','Начало независимой микроструктурной выборки','','column'),
('column.microstructure_end','ru','Конец подтверждения','Конец','Кон.','Конец независимой микроструктурной выборки','','column')
ON CONFLICT(resource_key,locale_code) DO UPDATE SET
 caption=excluded.caption,caption_short=excluded.caption_short,
 caption_mobile=excluded.caption_mobile,tooltip=excluded.tooltip,
 icon=excluded.icon,resource_group=excluded.resource_group;

INSERT INTO analytics.system_job_schedule_v1
    (job_code,executor_code,enabled,timezone_code,weekdays,window_start,window_end,
     interval_minutes,timeout_seconds,priority,config_version)
VALUES
    ('SESSION_EXECUTION_EDGE_MICROSTRUCTURE_V2','SESSION_EXECUTION_EDGE_V2',true,
     'Europe/Moscow','[0,1,2,3,4,5,6]'::jsonb,time '19:10',time '21:30',
     1440,1800,60,'V2_MICROSTRUCTURE_ONLY')
ON CONFLICT (job_code) DO UPDATE SET
    executor_code=excluded.executor_code,
    enabled=excluded.enabled,
    timezone_code=excluded.timezone_code,
    weekdays=excluded.weekdays,
    window_start=excluded.window_start,
    window_end=excluded.window_end,
    interval_minutes=excluded.interval_minutes,
    timeout_seconds=excluded.timeout_seconds,
    priority=excluded.priority,
    config_version=excluded.config_version,
    updated_at=clock_timestamp();

COMMIT;
