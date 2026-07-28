BEGIN;

CREATE TABLE IF NOT EXISTS analytics.temporal_oos_session_policy_v1(
    session_code text PRIMARY KEY,
    title_ru text NOT NULL,
    priority integer NOT NULL CHECK(priority > 0),
    minimum_future_bars integer NOT NULL CHECK(minimum_future_bars >= 100),
    enabled boolean NOT NULL DEFAULT true,
    config_version text NOT NULL,
    updated_at timestamptz NOT NULL DEFAULT clock_timestamp()
);

CREATE TABLE IF NOT EXISTS analytics.temporal_oos_algorithm_policy_v1(
    algorithm_code text PRIMARY KEY REFERENCES analytics.edge_search_algorithm_registry_v1(algorithm_code),
    priority integer NOT NULL CHECK(priority > 0),
    parameter_overlay jsonb NOT NULL CHECK(jsonb_typeof(parameter_overlay)='object'),
    enabled boolean NOT NULL DEFAULT true,
    config_version text NOT NULL,
    updated_at timestamptz NOT NULL DEFAULT clock_timestamp()
);

INSERT INTO analytics.temporal_oos_session_policy_v1
    (session_code,title_ru,priority,minimum_future_bars,config_version)
VALUES
    ('MOEX_OPEN','Открытие Москвы',10,500,'TEMPORAL_SESSION_POLICY_V1'),
    ('MOEX_FIRST_HOUR','Первый час Москвы',20,500,'TEMPORAL_SESSION_POLICY_V1'),
    ('EUROPE_OVERLAP','Европейская сессия',30,500,'TEMPORAL_SESSION_POLICY_V1'),
    ('US_OPEN','Открытие США',40,500,'TEMPORAL_SESSION_POLICY_V1'),
    ('EVENING','Вечерняя сессия',50,500,'TEMPORAL_SESSION_POLICY_V1')
ON CONFLICT(session_code) DO UPDATE SET
    title_ru=excluded.title_ru,priority=excluded.priority,
    minimum_future_bars=excluded.minimum_future_bars,enabled=true,
    config_version=excluded.config_version,updated_at=clock_timestamp();

INSERT INTO analytics.temporal_oos_algorithm_policy_v1
    (algorithm_code,priority,parameter_overlay,config_version)
VALUES
    ('DONCHIAN_VOL_BREAKOUT',10,
     '{"entry_policy_code":"META_ENTRY_V2","entry_trend_mode":"WITH_TREND","entry_volume_mode":"REQUIRE","entry_regime_mode":"REQUIRE","entry_allowed_regimes":["compression","range_compression","trend_up_expansion","trend_down_expansion"],"exit_policy_code":"DYNAMIC_EXIT_V1","exit_max_holding_bars":20,"exit_trend_lookback":5,"exit_volatility_risk_multiplier":2.0}'::jsonb,
     'TEMPORAL_ALGORITHM_POLICY_V1'),
    ('EMA_TREND',20,
     '{"entry_policy_code":"META_ENTRY_V2","entry_trend_mode":"WITH_TREND","entry_volume_mode":"REQUIRE","entry_min_volatility_bps":1.0,"entry_max_volatility_bps":120.0,"entry_regime_mode":"REQUIRE","entry_allowed_regimes":["trend_up","trend_down","trend_up_expansion","trend_down_expansion"],"exit_policy_code":"DYNAMIC_EXIT_V1","exit_max_holding_bars":20,"exit_trend_lookback":5,"exit_volatility_risk_multiplier":2.0}'::jsonb,
     'TEMPORAL_ALGORITHM_POLICY_V1')
ON CONFLICT(algorithm_code) DO UPDATE SET
    priority=excluded.priority,parameter_overlay=excluded.parameter_overlay,
    enabled=true,config_version=excluded.config_version,updated_at=clock_timestamp();

ALTER TABLE analytics.oos_remediation_candidate_v1
    DROP CONSTRAINT IF EXISTS oos_remediation_candidate_v1_branch_code_check;
ALTER TABLE analytics.oos_remediation_candidate_v1
    ADD CONSTRAINT oos_remediation_candidate_v1_branch_code_check
    CHECK(branch_code IN ('COST_REMEDIATION','SAMPLE_EXPANSION','TEMPORAL_SESSION'));

INSERT INTO analytics.edge_search_resource_policy_v1
    (branch_code,resource_share_pct,variant_budget,priority,policy_json)
VALUES
    ('TEMPORAL_SESSION',10,10,15,
     '{"future_only":true,"session_filter_required":true,"coarse_folds":2,"full_oos_top_share":0.10,"pass_gates_unchanged":true,"fingerprint_reuse":false}'::jsonb)
ON CONFLICT(branch_code) DO UPDATE SET
    resource_share_pct=excluded.resource_share_pct,variant_budget=excluded.variant_budget,
    priority=excluded.priority,policy_json=excluded.policy_json,enabled=true,
    updated_at=clock_timestamp();

UPDATE analytics.edge_search_resource_policy_v1
SET resource_share_pct=60,updated_at=clock_timestamp()
WHERE branch_code='COST_REMEDIATION' AND resource_share_pct=70;

CREATE OR REPLACE VIEW analytics.oos_remediation_branch_summary_v1 AS
WITH latest_by_branch AS (
  SELECT DISTINCT ON (c.branch_code) c.branch_code,c.process_id
  FROM analytics.oos_remediation_candidate_v1 c
  JOIN analytics.oos_remediation_process_v1 p USING(process_id)
  ORDER BY c.branch_code,p.started_at DESC,c.updated_at DESC
)
SELECT p.process_id,l.branch_code,p.status_code AS process_status,p.current_step_code,
       p.progress_pct,p.started_at,p.updated_at,
       count(DISTINCT c.parent_result_id) AS source_failures,
       count(c.candidate_id) AS created_variants,
       count(c.candidate_id) FILTER(WHERE c.status_code LIKE 'PRUNED_%') AS pruned_variants,
       count(c.candidate_id) FILTER(WHERE c.status_code IN ('WAITING_FUTURE_DATA','QUEUED')) AS queued_variants,
       count(c.candidate_id) FILTER(WHERE c.status_code IN ('EVALUATED_FAIL','OOS_PASS')) AS evaluated_variants,
       count(c.candidate_id) FILTER(WHERE c.status_code='OOS_PASS') AS oos_pass
FROM latest_by_branch l
JOIN analytics.oos_remediation_process_v1 p USING(process_id)
LEFT JOIN analytics.oos_remediation_candidate_v1 c
  ON c.process_id=p.process_id AND c.branch_code=l.branch_code
GROUP BY p.process_id,l.branch_code,p.status_code,p.current_step_code,
         p.progress_pct,p.started_at,p.updated_at;

INSERT INTO analytics.system_job_schedule_v1(
 job_code,executor_code,enabled,timezone_code,weekdays,window_start,window_end,
 interval_minutes,timeout_seconds,priority,config_version)
VALUES('TEMPORAL_OOS_BRANCH_GENERATOR','TEMPORAL_OOS_BRANCH_GENERATOR_V1',true,
 'Europe/Moscow','[0,1,2,3,4,5,6]'::jsonb,time '00:00',time '23:59',15,120,35,
 'TEMPORAL_OOS_BRANCHES_V1')
ON CONFLICT(job_code) DO UPDATE SET executor_code=excluded.executor_code,enabled=true,
 timezone_code=excluded.timezone_code,weekdays=excluded.weekdays,
 window_start=excluded.window_start,window_end=excluded.window_end,
 interval_minutes=excluded.interval_minutes,timeout_seconds=excluded.timeout_seconds,
 priority=excluded.priority,config_version=excluded.config_version,updated_at=clock_timestamp();

INSERT INTO presentation.ui_resource_v1
(resource_key,locale_code,caption,caption_short,caption_mobile,tooltip,icon,resource_group)
VALUES
('research.remediation.branch.temporal_session','ru','Время входа','Сессии','Время','Отдельный future-only OOS для заранее заданных торговых сессий; критерии PASS не меняются','','research'),
('research.remediation.branch.temporal_session','en','Entry time','Sessions','Time','Separate future-only OOS for predeclared market sessions with unchanged PASS gates','','research')
ON CONFLICT(resource_key,locale_code) DO UPDATE SET caption=excluded.caption,
 caption_short=excluded.caption_short,caption_mobile=excluded.caption_mobile,
 tooltip=excluded.tooltip,icon=excluded.icon,resource_group=excluded.resource_group;

GRANT SELECT ON analytics.temporal_oos_session_policy_v1 TO alex,finam;
GRANT SELECT ON analytics.temporal_oos_algorithm_policy_v1 TO alex,finam;

COMMIT;
