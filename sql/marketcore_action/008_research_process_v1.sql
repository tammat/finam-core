BEGIN;

CREATE TABLE IF NOT EXISTS marketcore_action.research_process_v1 (
    process_id UUID PRIMARY KEY,
    process_type TEXT NOT NULL CHECK (process_type IN ('EDGE_SEARCH','RESEARCH_REFRESH')),
    actor_id TEXT NOT NULL DEFAULT 'system',
    recommendation_code TEXT NOT NULL,
    selected_action_id TEXT,
    command_request_id TEXT,
    cycle_id UUID,
    run_id UUID,
    status_code TEXT NOT NULL CHECK (status_code IN ('PENDING','RUNNING','SUCCEEDED','FAILED','SKIPPED')),
    progress_pct NUMERIC(5,2) NOT NULL DEFAULT 0 CHECK (progress_pct BETWEEN 0 AND 100),
    current_step_code TEXT,
    outcome_code TEXT,
    reason_code TEXT,
    explanation_ru TEXT,
    requested_at TIMESTAMPTZ NOT NULL DEFAULT clock_timestamp(),
    started_at TIMESTAMPTZ,
    finished_at TIMESTAMPTZ,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT clock_timestamp()
);

CREATE TABLE IF NOT EXISTS marketcore_action.research_process_event_v1 (
    event_id BIGSERIAL PRIMARY KEY,
    process_id UUID NOT NULL REFERENCES marketcore_action.research_process_v1(process_id),
    event_code TEXT NOT NULL,
    status_code TEXT NOT NULL,
    progress_pct NUMERIC(5,2) NOT NULL,
    step_code TEXT,
    payload JSONB NOT NULL DEFAULT '{}'::jsonb,
    occurred_at TIMESTAMPTZ NOT NULL DEFAULT clock_timestamp()
);

CREATE TABLE IF NOT EXISTS marketcore_action.research_recommendation_action_v1 (
    recommendation_code TEXT NOT NULL,
    action_order INTEGER NOT NULL CHECK (action_order > 0),
    action_id TEXT NOT NULL,
    command_code TEXT NOT NULL,
    policy_class TEXT NOT NULL,
    rollback_code TEXT NOT NULL,
    locale_code TEXT NOT NULL DEFAULT 'ru',
    label TEXT NOT NULL,
    detail TEXT NOT NULL,
    enabled BOOLEAN NOT NULL DEFAULT TRUE,
    PRIMARY KEY (recommendation_code,action_order,locale_code)
);

ALTER TABLE marketcore_action.command_request_v2
    ADD COLUMN IF NOT EXISTS process_id UUID REFERENCES marketcore_action.research_process_v1(process_id);
ALTER TABLE analytics.edge_search_scenario_run_v1
    ADD COLUMN IF NOT EXISTS process_id UUID REFERENCES marketcore_action.research_process_v1(process_id);
ALTER TABLE marketcore_action.research_process_v1
    ADD COLUMN IF NOT EXISTS actor_id TEXT NOT NULL DEFAULT 'system';

CREATE OR REPLACE FUNCTION marketcore_action.ensure_research_process_v1()
RETURNS TRIGGER LANGUAGE plpgsql AS $$
BEGIN
    IF NEW.request_kind IN ('EDGE_SEARCH_RUN','RESEARCH_REFRESH') AND NEW.process_id IS NULL THEN
        NEW.process_id := NEW.request_id::uuid;
        INSERT INTO marketcore_action.research_process_v1 (
            process_id,process_type,actor_id,recommendation_code,selected_action_id,
            command_request_id,status_code,progress_pct,current_step_code,requested_at,updated_at
        ) VALUES (
            NEW.process_id,
            CASE NEW.request_kind WHEN 'EDGE_SEARCH_RUN' THEN 'EDGE_SEARCH' ELSE 'RESEARCH_REFRESH' END,NEW.actor_id,
            CASE NEW.request_kind WHEN 'EDGE_SEARCH_RUN' THEN 'KEEP_GATES_AND_EXPAND_EVIDENCE' ELSE 'WAIT_FOR_SYSTEM_ANALYSIS' END,
            NEW.action_id,NEW.request_id,'PENDING',0,'QUEUED',NEW.requested_at,clock_timestamp()
        ) ON CONFLICT (process_id) DO NOTHING;
    END IF;
    RETURN NEW;
END;
$$;

DROP TRIGGER IF EXISTS command_request_research_process_v1 ON marketcore_action.command_request_v2;
CREATE TRIGGER command_request_research_process_v1
BEFORE INSERT ON marketcore_action.command_request_v2
FOR EACH ROW EXECUTE FUNCTION marketcore_action.ensure_research_process_v1();

INSERT INTO marketcore_action.research_recommendation_action_v1
 (recommendation_code,action_order,action_id,command_code,policy_class,rollback_code,locale_code,label,detail)
VALUES
 ('KEEP_GATES_AND_EXPAND_EVIDENCE',1,'research.edge_search.run','RESEARCH.RUN_EDGE_SEARCH','RESEARCH_MAINTENANCE','RESEARCH.CANCEL_PENDING_REQUEST','ru','Запустить поиск','Расширить выборку без ослабления критериев'),
 ('KEEP_GATES_AND_EXPAND_EVIDENCE',2,'research.request.refresh','RESEARCH.REQUEST_REFRESH','RESEARCH_MAINTENANCE','RESEARCH.CANCEL_PENDING_REQUEST','ru','Обновить данные','Пересчитать исследовательские источники'),
 ('RETRY_ON_NEXT_SYSTEM_SCHEDULE',1,'research.edge_search.run','RESEARCH.RUN_EDGE_SEARCH','RESEARCH_MAINTENANCE','RESEARCH.CANCEL_PENDING_REQUEST','ru','Повторить поиск','Поставить безопасный цикл в очередь'),
 ('FIX_EXECUTOR_AND_RETRY_SYSTEM_SCHEDULE',1,'research.request.refresh','RESEARCH.REQUEST_REFRESH','RESEARCH_MAINTENANCE','RESEARCH.CANCEL_PENDING_REQUEST','ru','Обновить данные','Восстановить входные данные исполнителя'),
 ('FIX_EXECUTOR_AND_RETRY_SYSTEM_SCHEDULE',2,'research.edge_search.run','RESEARCH.RUN_EDGE_SEARCH','RESEARCH_MAINTENANCE','RESEARCH.CANCEL_PENDING_REQUEST','ru','Повторить поиск','Повторить цикл после восстановления данных'),
 ('WAIT_FOR_SYSTEM_ANALYSIS',1,'research.request.refresh','RESEARCH.REQUEST_REFRESH','RESEARCH_MAINTENANCE','RESEARCH.CANCEL_PENDING_REQUEST','ru','Обновить анализ','Получить актуальный системный анализ')
ON CONFLICT (recommendation_code,action_order,locale_code) DO UPDATE SET
 action_id=EXCLUDED.action_id,command_code=EXCLUDED.command_code,
 policy_class=EXCLUDED.policy_class,rollback_code=EXCLUDED.rollback_code,
 label=EXCLUDED.label,detail=EXCLUDED.detail,enabled=EXCLUDED.enabled;

WITH source AS (
 SELECT r.run_id,r.cycle_id,r.status_code,r.started_at,r.finished_at,
        coalesce(m.request_id::uuid,r.run_id) process_id,
        a.recommendation_code,a.outcome_code,a.primary_reason_code,a.explanation_ru,
        coalesce(c.progress_pct,CASE WHEN r.finished_at IS NULL THEN 0 ELSE 100 END) progress_pct,
        c.current_step
 FROM analytics.edge_search_scenario_run_v1 r
 LEFT JOIN marketcore_action.edge_search_request_run_v1 m ON m.run_id=r.run_id
 LEFT JOIN analytics.edge_search_run_analysis_v1 a ON a.run_id=r.run_id
 LEFT JOIN analytics.edge_search_cycle_status_v1 c ON c.cycle_id=r.cycle_id
)
INSERT INTO marketcore_action.research_process_v1
 (process_id,process_type,actor_id,recommendation_code,cycle_id,run_id,status_code,progress_pct,current_step_code,
  outcome_code,reason_code,explanation_ru,requested_at,started_at,finished_at,updated_at)
SELECT process_id,'EDGE_SEARCH','system',coalesce(recommendation_code,'WAIT_FOR_SYSTEM_ANALYSIS'),cycle_id,run_id,
       status_code,progress_pct,current_step,outcome_code,primary_reason_code,explanation_ru,
       started_at,started_at,finished_at,coalesce(finished_at,started_at)
FROM source
ON CONFLICT (process_id) DO UPDATE SET
 cycle_id=EXCLUDED.cycle_id,run_id=EXCLUDED.run_id,status_code=EXCLUDED.status_code,
 progress_pct=EXCLUDED.progress_pct,current_step_code=EXCLUDED.current_step_code,
 outcome_code=EXCLUDED.outcome_code,reason_code=EXCLUDED.reason_code,
 recommendation_code=EXCLUDED.recommendation_code,explanation_ru=EXCLUDED.explanation_ru,
 started_at=EXCLUDED.started_at,finished_at=EXCLUDED.finished_at,updated_at=EXCLUDED.updated_at;

UPDATE analytics.edge_search_scenario_run_v1 r SET process_id=coalesce(m.request_id::uuid,r.run_id)
FROM (SELECT run_id,request_id FROM marketcore_action.edge_search_request_run_v1) m
WHERE m.run_id=r.run_id;
UPDATE analytics.edge_search_scenario_run_v1 SET process_id=run_id WHERE process_id IS NULL;

INSERT INTO marketcore_action.research_process_v1
 (process_id,process_type,actor_id,recommendation_code,selected_action_id,command_request_id,status_code,
  progress_pct,requested_at,started_at,finished_at,updated_at)
SELECT request_id::uuid,
       CASE request_kind WHEN 'EDGE_SEARCH_RUN' THEN 'EDGE_SEARCH' ELSE 'RESEARCH_REFRESH' END,
       actor_id,
       CASE request_kind WHEN 'EDGE_SEARCH_RUN' THEN 'KEEP_GATES_AND_EXPAND_EVIDENCE' ELSE 'WAIT_FOR_SYSTEM_ANALYSIS' END,
       action_id,request_id,
       CASE status WHEN 'COMPLETED' THEN 'SUCCEEDED' WHEN 'CANCELLED' THEN 'SKIPPED' ELSE status END,
       CASE WHEN status IN ('COMPLETED','FAILED','CANCELLED') THEN 100 WHEN status='RUNNING' THEN 5 ELSE 0 END,
       requested_at,started_at,finished_at,coalesce(finished_at,started_at,requested_at)
FROM marketcore_action.command_request_v2
WHERE request_kind IN ('EDGE_SEARCH_RUN','RESEARCH_REFRESH')
ON CONFLICT (process_id) DO UPDATE SET
 command_request_id=EXCLUDED.command_request_id,selected_action_id=EXCLUDED.selected_action_id,
 actor_id=EXCLUDED.actor_id;

UPDATE marketcore_action.command_request_v2
SET process_id=request_id::uuid
WHERE request_kind IN ('EDGE_SEARCH_RUN','RESEARCH_REFRESH') AND process_id IS NULL;

CREATE INDEX IF NOT EXISTS research_process_status_updated_idx
 ON marketcore_action.research_process_v1(status_code,updated_at DESC);
CREATE INDEX IF NOT EXISTS research_process_event_process_time_idx
 ON marketcore_action.research_process_event_v1(process_id,occurred_at DESC);
CREATE INDEX IF NOT EXISTS command_request_v2_process_idx
 ON marketcore_action.command_request_v2(process_id,requested_at DESC);

GRANT SELECT,INSERT,UPDATE ON marketcore_action.research_process_v1,
 marketcore_action.research_process_event_v1 TO alex;
GRANT SELECT ON marketcore_action.research_recommendation_action_v1 TO alex;
GRANT USAGE,SELECT ON SEQUENCE marketcore_action.research_process_event_v1_event_id_seq TO alex;

COMMIT;
