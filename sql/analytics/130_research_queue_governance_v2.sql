BEGIN;

ALTER TABLE marketcore_action.command_request_v2
    ADD COLUMN IF NOT EXISTS priority integer NOT NULL DEFAULT 50;

CREATE TABLE IF NOT EXISTS analytics.research_queue_governance_policy_v2(
    policy_code text PRIMARY KEY,
    enabled boolean NOT NULL DEFAULT true,
    legacy_stale_days integer NOT NULL CHECK(legacy_stale_days >= 1),
    pending_stale_minutes integer NOT NULL CHECK(pending_stale_minutes >= 30),
    max_pending integer NOT NULL CHECK(max_pending BETWEEN 1 AND 1000),
    priority_by_kind jsonb NOT NULL CHECK(jsonb_typeof(priority_by_kind)='object'),
    config_version text NOT NULL,
    updated_at timestamptz NOT NULL DEFAULT clock_timestamp()
);

INSERT INTO analytics.research_queue_governance_policy_v2
    (policy_code,legacy_stale_days,pending_stale_minutes,max_pending,priority_by_kind,config_version)
VALUES ('DEFAULT',1,360,25,
    '{"EDGE_SEARCH_CANCEL":1,"OPERATOR_DECISION_ACKNOWLEDGE":5,"OPERATOR_DECISION_MEASURE":5,
      "RESEARCH_UNIVERSE_INCLUDE":10,"RESEARCH_UNIVERSE_EXCLUDE":10,"RESEARCH_UNIVERSE_PRIORITY":10,
      "PAPER_OBSERVATION":20,"RESEARCH_REFRESH":30,"EDGE_SEARCH_RUN":50}'::jsonb,
    'RESEARCH_QUEUE_GOVERNANCE_V2')
ON CONFLICT(policy_code) DO UPDATE SET enabled=true,
    legacy_stale_days=excluded.legacy_stale_days,
    pending_stale_minutes=excluded.pending_stale_minutes,max_pending=excluded.max_pending,
    priority_by_kind=excluded.priority_by_kind,config_version=excluded.config_version,
    updated_at=clock_timestamp();

CREATE TABLE IF NOT EXISTS analytics.research_queue_governance_run_v2(
    run_id uuid PRIMARY KEY,
    policy_code text NOT NULL REFERENCES analytics.research_queue_governance_policy_v2(policy_code),
    status_code text NOT NULL CHECK(status_code IN ('RUNNING','COMPLETE','FAILED')),
    active_before integer NOT NULL DEFAULT 0,
    active_after integer NOT NULL DEFAULT 0,
    legacy_archived integer NOT NULL DEFAULT 0,
    lab_runs_archived integer NOT NULL DEFAULT 0,
    duplicates_cancelled integer NOT NULL DEFAULT 0,
    stale_cancelled integer NOT NULL DEFAULT 0,
    capacity_cancelled integer NOT NULL DEFAULT 0,
    started_at timestamptz NOT NULL DEFAULT clock_timestamp(),
    finished_at timestamptz
);

CREATE OR REPLACE FUNCTION marketcore_action.assign_command_priority_v2()
RETURNS trigger LANGUAGE plpgsql AS $$
DECLARE assigned integer;
BEGIN
    SELECT (priority_by_kind->>NEW.request_kind)::integer INTO assigned
    FROM analytics.research_queue_governance_policy_v2
    WHERE enabled ORDER BY updated_at DESC LIMIT 1;
    NEW.priority := coalesce(assigned,50);
    RETURN NEW;
END $$;

DROP TRIGGER IF EXISTS command_request_priority_v2 ON marketcore_action.command_request_v2;
CREATE TRIGGER command_request_priority_v2 BEFORE INSERT ON marketcore_action.command_request_v2
FOR EACH ROW EXECUTE FUNCTION marketcore_action.assign_command_priority_v2();

CREATE INDEX IF NOT EXISTS command_request_v2_priority_pending_idx
ON marketcore_action.command_request_v2(priority,requested_at)
WHERE status='PENDING';

CREATE UNIQUE INDEX IF NOT EXISTS command_request_v2_one_active_target_v2_idx
ON marketcore_action.command_request_v2(request_kind,coalesce(target_id,''))
WHERE status IN ('PENDING','RUNNING');

INSERT INTO analytics.system_job_schedule_v1
    (job_code,executor_code,enabled,interval_minutes,timezone_code,weekdays,
     window_start,window_end,priority,timeout_seconds,config_version)
VALUES ('RESEARCH_QUEUE_GOVERNOR','RESEARCH_QUEUE_GOVERNOR_V2',true,5,'Europe/Moscow',
    '[0,1,2,3,4,5,6]'::jsonb,time '00:00',time '23:59',4,60,'V2_DB_DRIVEN')
ON CONFLICT(job_code) DO UPDATE SET executor_code=excluded.executor_code,enabled=true,
    interval_minutes=excluded.interval_minutes,timezone_code=excluded.timezone_code,
    weekdays=excluded.weekdays,window_start=excluded.window_start,window_end=excluded.window_end,
    priority=excluded.priority,timeout_seconds=excluded.timeout_seconds,
    config_version=excluded.config_version,updated_at=clock_timestamp();

GRANT SELECT ON analytics.research_queue_governance_policy_v2 TO alex;
GRANT SELECT,INSERT,UPDATE ON analytics.research_queue_governance_run_v2 TO alex;

COMMIT;
