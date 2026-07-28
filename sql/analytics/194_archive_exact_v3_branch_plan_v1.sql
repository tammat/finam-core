BEGIN;

CREATE TABLE IF NOT EXISTS analytics.archive_exact_v3_branch_plan_v1 (
    branch_id uuid PRIMARY KEY,
    archive_hypothesis_id uuid NOT NULL UNIQUE,
    portfolio_scope text NOT NULL,
    symbol text NOT NULL,
    strategy_code text NOT NULL,
    side_code text NOT NULL,
    session_code text,
    regime_code text,
    exit_rule text,
    accumulated_trades integer NOT NULL DEFAULT 0,
    target_trades integer NOT NULL DEFAULT 80,
    priority_score numeric,
    status_code text NOT NULL CHECK (status_code IN ('ACTIVE','ACTIVE_SPLIT_REGIME','WAITING_CONTEXT_DEFINITION','READY_FOR_OOS')),
    reason_code text NOT NULL,
    updated_at timestamptz NOT NULL DEFAULT clock_timestamp()
);

CREATE INDEX IF NOT EXISTS archive_exact_v3_branch_priority_idx
    ON analytics.archive_exact_v3_branch_plan_v1(status_code,priority_score DESC,updated_at DESC);

INSERT INTO analytics.system_job_schedule_v1(
    job_code,executor_code,enabled,timezone_code,weekdays,window_start,window_end,
    interval_minutes,timeout_seconds,priority,config_version
) VALUES (
    'ARCHIVE_EXACT_V3_BRANCH_PLAN','ARCHIVE_EXACT_V3_BRANCH_PLAN_V1',true,
    'Europe/Moscow','[0,1,2,3,4,5,6]'::jsonb,'00:00','23:59',2,60,8,
    'ARCHIVE_EXACT_V3_BRANCH_PLAN_V1'
)
ON CONFLICT(job_code) DO UPDATE SET executor_code=excluded.executor_code,enabled=true,
    interval_minutes=excluded.interval_minutes,timeout_seconds=excluded.timeout_seconds,
    priority=excluded.priority,config_version=excluded.config_version,updated_at=clock_timestamp();

GRANT SELECT,INSERT,UPDATE ON analytics.archive_exact_v3_branch_plan_v1 TO alex;
GRANT SELECT,INSERT,UPDATE ON analytics.archive_exact_v3_branch_plan_v1 TO finam;

COMMIT;
