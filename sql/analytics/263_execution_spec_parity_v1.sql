BEGIN;

CREATE TABLE IF NOT EXISTS analytics.execution_spec_parity_v1 (
  parity_id bigserial PRIMARY KEY,
  admission_id uuid NOT NULL,
  profile_id bigint,
  source_signal_id bigint,
  research_spec jsonb NOT NULL,
  research_spec_hash text NOT NULL,
  runtime_spec jsonb,
  runtime_spec_hash text,
  verdict_code text NOT NULL CHECK(verdict_code IN ('MATCH','MISMATCH','NOT_PROVEN')),
  reason_codes jsonb NOT NULL DEFAULT '[]'::jsonb,
  source_version text NOT NULL DEFAULT 'EXECUTION_SPEC_PARITY_V1',
  checked_at timestamptz NOT NULL DEFAULT clock_timestamp(),
  UNIQUE(admission_id,profile_id,source_signal_id)
);

CREATE INDEX IF NOT EXISTS execution_spec_parity_latest_v1_idx
ON analytics.execution_spec_parity_v1(admission_id,checked_at DESC);

INSERT INTO analytics.system_job_schedule_v1(
  job_code,executor_code,enabled,timezone_code,weekdays,window_start,window_end,
  interval_minutes,timeout_seconds,priority,config_version)
VALUES('EXECUTION_SPEC_PARITY_REPLAY','EXECUTION_SPEC_PARITY_REPLAY_V1',true,
       'Europe/Moscow','[0,1,2,3,4,5,6]'::jsonb,'00:00','23:59',5,60,1,
       'EXECUTION_SPEC_PARITY_V1')
ON CONFLICT(job_code) DO UPDATE SET executor_code=excluded.executor_code,
  enabled=excluded.enabled,interval_minutes=excluded.interval_minutes,
  timeout_seconds=excluded.timeout_seconds,priority=excluded.priority,
  config_version=excluded.config_version,updated_at=clock_timestamp();

GRANT SELECT,INSERT,UPDATE ON analytics.execution_spec_parity_v1 TO alex,finam;
GRANT SELECT ON analytics.execution_spec_parity_v1 TO finam_user;
GRANT USAGE,SELECT ON SEQUENCE analytics.execution_spec_parity_v1_parity_id_seq TO alex,finam;

COMMIT;
