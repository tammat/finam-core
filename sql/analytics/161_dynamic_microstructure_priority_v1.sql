BEGIN;

CREATE TABLE IF NOT EXISTS analytics.microstructure_priority_policy_v1 (
    policy_code text PRIMARY KEY,
    enabled boolean NOT NULL DEFAULT true,
    detail_slots integer NOT NULL CHECK (detail_slots BETWEEN 1 AND 16),
    analysis_slots integer NOT NULL CHECK (analysis_slots BETWEEN 1 AND 16),
    refresh_seconds integer NOT NULL CHECK (refresh_seconds BETWEEN 60 AND 3600),
    weights jsonb NOT NULL,
    updated_at timestamptz NOT NULL DEFAULT clock_timestamp()
);

INSERT INTO analytics.microstructure_priority_policy_v1
    (policy_code,enabled,detail_slots,analysis_slots,refresh_seconds,weights)
VALUES
    ('DYNAMIC_EDGE_PRIORITY_V1',true,8,4,300,
     '{"oos_deficit":0.30,"coverage_gap":0.25,"information_value":0.20,"freshness":0.10,"signal_activity":0.10,"capacity":0.05}'::jsonb)
ON CONFLICT (policy_code) DO UPDATE SET
    enabled=excluded.enabled,
    detail_slots=excluded.detail_slots,
    analysis_slots=excluded.analysis_slots,
    refresh_seconds=excluded.refresh_seconds,
    weights=excluded.weights,
    updated_at=clock_timestamp();

CREATE TABLE IF NOT EXISTS analytics.microstructure_priority_decision_v1 (
    decision_batch_id uuid NOT NULL,
    decided_at timestamptz NOT NULL DEFAULT clock_timestamp(),
    symbol text NOT NULL,
    priority_rank integer NOT NULL,
    priority_score numeric NOT NULL,
    selected_for_detail boolean NOT NULL,
    selected_for_analysis boolean NOT NULL,
    reason_code text NOT NULL,
    evidence jsonb NOT NULL,
    policy_code text NOT NULL REFERENCES analytics.microstructure_priority_policy_v1(policy_code),
    PRIMARY KEY (decision_batch_id,symbol)
);

CREATE INDEX IF NOT EXISTS microstructure_priority_decision_recent_v1
    ON analytics.microstructure_priority_decision_v1(decided_at DESC,priority_rank);

CREATE OR REPLACE VIEW analytics.microstructure_research_priority_v1 AS
WITH policy AS (
    SELECT * FROM analytics.microstructure_priority_policy_v1
    WHERE policy_code='DYNAMIC_EDGE_PRIORITY_V1' AND enabled
), latest_scout_run AS (
    SELECT run_id FROM analytics.instrument_scout_result_v1
    ORDER BY created_at DESC LIMIT 1
), universe AS (
    SELECT symbol FROM analytics.instrument_scout_result_v1
    WHERE run_id=(SELECT run_id FROM latest_scout_run)
      AND decision_code IN ('SELECTED','RESERVE')
    UNION
    SELECT symbol FROM analytics.oos_remediation_candidate_v1
    WHERE status_code='WAITING_FUTURE_DATA'
    UNION
    SELECT symbol FROM public.market_data_watch_universe WHERE is_enabled
    UNION
    SELECT DISTINCT symbol FROM public.signal_fills
    WHERE created_at >= now()-interval '1 day'
), scout AS (
    SELECT DISTINCT ON (symbol) symbol,information_value_score,capacity_rub,
           max_abs_correlation,decision_code
    FROM analytics.instrument_scout_result_v1
    WHERE run_id=(SELECT run_id FROM latest_scout_run)
    ORDER BY symbol,created_at DESC
), deficit AS (
    SELECT symbol,count(*) AS waiting_candidates
    FROM analytics.oos_remediation_candidate_v1
    WHERE status_code='WAITING_FUTURE_DATA'
    GROUP BY symbol
), latest_micro_run AS (
    SELECT discovery_run_id FROM analytics.execution_edge_result_v1
    WHERE cohort_code='MICROSTRUCTURE_ONLY'
    ORDER BY created_at DESC LIMIT 1
), coverage AS (
    SELECT symbol,avg(microstructure_coverage_ratio) AS coverage_ratio,
           sum(microstructure_matched_trades) AS matched_trades,
           sum(eligible_oos_trades) AS eligible_trades
    FROM analytics.execution_edge_result_v1
    WHERE cohort_code='MICROSTRUCTURE_ONLY'
      AND discovery_run_id=(SELECT discovery_run_id FROM latest_micro_run)
    GROUP BY symbol
), activity AS (
    SELECT symbol,count(*) AS fills_1h
    FROM public.signal_fills
    WHERE created_at >= now()-interval '1 hour'
    GROUP BY symbol
), freshness AS (
    SELECT symbol,max(observed_at) AS last_quote_at,
           count(*) FILTER (WHERE observed_at >= now()-interval '15 minutes'
             AND bid_levels>0 AND ask_levels>0 AND bid_depth>0 AND ask_depth>0) AS deep_quotes_15m
    FROM analytics.market_microstructure_snapshot_v1
    WHERE observed_at >= now()-interval '1 day'
    GROUP BY symbol
), components AS (
    SELECT u.symbol,
           coalesce(d.waiting_candidates,0) AS waiting_candidates,
           coalesce(c.coverage_ratio,0) AS coverage_ratio,
           coalesce(c.matched_trades,0) AS matched_trades,
           coalesce(c.eligible_trades,0) AS eligible_trades,
           coalesce(s.information_value_score,0) AS information_value_score,
           coalesce(s.capacity_rub,0) AS capacity_rub,
           coalesce(s.max_abs_correlation,1) AS max_abs_correlation,
           coalesce(a.fills_1h,0) AS fills_1h,
           f.last_quote_at,coalesce(f.deep_quotes_15m,0) AS deep_quotes_15m,
           least(1.0,coalesce(d.waiting_candidates,0)/10.0) AS oos_deficit_component,
           greatest(0.0,1.0-coalesce(c.coverage_ratio,0)) AS coverage_gap_component,
           least(1.0,coalesce(s.information_value_score,0)/100.0) AS information_component,
           CASE WHEN f.last_quote_at >= now()-interval '2 minutes' THEN 1.0 ELSE 0.0 END AS freshness_component,
           least(1.0,coalesce(a.fills_1h,0)/100.0) AS activity_component,
           least(1.0,coalesce(s.capacity_rub,0)/200000.0) AS capacity_component
    FROM universe u
    LEFT JOIN scout s USING(symbol)
    LEFT JOIN deficit d USING(symbol)
    LEFT JOIN coverage c USING(symbol)
    LEFT JOIN activity a USING(symbol)
    LEFT JOIN freshness f USING(symbol)
), scored AS (
    SELECT c.*,
           round(100*(
               c.oos_deficit_component*(p.weights->>'oos_deficit')::numeric+
               c.coverage_gap_component*(p.weights->>'coverage_gap')::numeric+
               c.information_component*(p.weights->>'information_value')::numeric+
               c.freshness_component*(p.weights->>'freshness')::numeric+
               c.activity_component*(p.weights->>'signal_activity')::numeric+
               c.capacity_component*(p.weights->>'capacity')::numeric
           ),4) AS priority_score,
           CASE
             WHEN c.waiting_candidates>0 AND c.coverage_ratio<0.80 THEN 'OOS_DATA_DEFICIT'
             WHEN c.coverage_ratio<0.80 THEN 'MICROSTRUCTURE_COVERAGE_GAP'
             WHEN c.fills_1h>0 THEN 'ACTIVE_SIGNAL_FLOW'
             WHEN c.information_value_score>=60 THEN 'HIGH_INFORMATION_VALUE'
             ELSE 'DIVERSIFICATION_RESERVE'
           END AS reason_code,
           p.policy_code,p.detail_slots,p.analysis_slots
    FROM components c CROSS JOIN policy p
), ranked AS (
    SELECT scored.*,row_number() OVER (
        ORDER BY priority_score DESC,waiting_candidates DESC,
                 information_value_score DESC,symbol
    ) AS priority_rank
    FROM scored
)
SELECT symbol,priority_rank,priority_score,
       priority_rank<=detail_slots AS selected_for_detail,
       priority_rank<=analysis_slots AS selected_for_analysis,
       reason_code,waiting_candidates,round(100*coverage_ratio,2) AS coverage_pct,
       matched_trades,eligible_trades,information_value_score,capacity_rub,
       max_abs_correlation,fills_1h,last_quote_at,deep_quotes_15m,
       policy_code
FROM ranked;

GRANT SELECT ON analytics.microstructure_research_priority_v1 TO alex,finam;
GRANT SELECT ON analytics.microstructure_priority_policy_v1 TO alex,finam;
GRANT SELECT,INSERT ON analytics.microstructure_priority_decision_v1 TO alex;

INSERT INTO analytics.system_job_schedule_v1
    (job_code,executor_code,enabled,timezone_code,weekdays,window_start,window_end,
     interval_minutes,timeout_seconds,priority,config_version)
VALUES
    ('MICROSTRUCTURE_PRIORITY_REFRESH_V1','MICROSTRUCTURE_PRIORITY_REFRESH_V1',true,
     'Europe/Moscow','[0,1,2,3,4,5,6]'::jsonb,time '06:45',time '23:55',
     5,30,18,'DYNAMIC_EDGE_PRIORITY_V1')
ON CONFLICT (job_code) DO UPDATE SET
    executor_code=excluded.executor_code,enabled=excluded.enabled,
    timezone_code=excluded.timezone_code,weekdays=excluded.weekdays,
    window_start=excluded.window_start,window_end=excluded.window_end,
    interval_minutes=excluded.interval_minutes,timeout_seconds=excluded.timeout_seconds,
    priority=excluded.priority,config_version=excluded.config_version,
    updated_at=clock_timestamp();

INSERT INTO presentation.ui_resource_v1
(resource_key,locale_code,caption,caption_short,caption_mobile,tooltip,icon,resource_group)
VALUES
('research.control.section.microstructure_priorities.title','ru','Приоритеты стакана','Приоритеты','Приоритеты','Динамический рейтинг инструментов для подтверждения реального исполнения','','research'),
('research.control.section.microstructure_priorities.title','en','Order-book priorities','Priorities','Priorities','Dynamic instrument ranking for real-execution validation','','research'),
('column.priority_rank','ru','Приоритет','№','№','Текущая позиция в динамическом рейтинге','','column'),
('column.priority_score','ru','Оценка','Оценка','Балл','Интегральная перспективность следующего сбора данных','','column'),
('column.selected_for_detail','ru','Стакан','Стакан','Стакан','Получает детальную подписку bid/ask и глубины','','column'),
('column.selected_for_analysis','ru','Расчёт','Расчёт','Расчёт','Включён в следующий микроструктурный анализ','','column'),
('column.detail_status','ru','Стакан','Стакан','Стакан','Получает детальную подписку bid/ask и глубины','','column'),
('column.analysis_status','ru','Расчёт','Расчёт','Расчёт','Включён в следующий микроструктурный анализ','','column'),
('column.waiting_candidates','ru','Ожидают OOS','OOS','OOS','Количество вариантов, ожидающих новых данных','','column'),
('column.coverage_pct','ru','Покрытие, %','Покрытие','Покр.','Доля OOS-сделок, подтверждённых стаканом','','column'),
('column.fills_1h','ru','Сделки за час','Сделки','Сделки','Свежая активность Paper-сделок','','column'),
('status.oos_data_deficit','ru','Дефицит OOS','Дефицит','OOS','Активные кандидаты ожидают подтверждающие данные','','status'),
('status.microstructure_coverage_gap','ru','Мало стакана','Мало данных','Стакан','Покрытие реальным стаканом ниже методологического порога','','status'),
('status.active_signal_flow','ru','Свежие сделки','Активность','Сделки','Инструмент создаёт свежий поток сделок','','status'),
('status.high_information_value','ru','Перспективный рынок','Перспективный','Рынок','Высокая информационная ценность исследования','','status'),
('status.diversification_reserve','ru','Резерв','Резерв','Резерв','Резерв диверсификации исследовательской вселенной','','status')
ON CONFLICT(resource_key,locale_code) DO UPDATE SET
 caption=excluded.caption,caption_short=excluded.caption_short,
 caption_mobile=excluded.caption_mobile,tooltip=excluded.tooltip,
 icon=excluded.icon,resource_group=excluded.resource_group;

COMMIT;
