BEGIN;
CREATE TABLE IF NOT EXISTS analytics.observation_parity_v1(
  parity_id bigserial PRIMARY KEY,
  admission_id uuid NOT NULL,
  source_signal_id bigint NOT NULL,
  signal_id text NOT NULL,
  candidate_code text NOT NULL,
  research_observation jsonb NOT NULL,
  runtime_observation jsonb,
  verdict_code text NOT NULL CHECK(verdict_code IN ('MATCH','MISMATCH','NOT_PROVEN')),
  reason_codes jsonb NOT NULL,
  checked_at timestamptz NOT NULL DEFAULT clock_timestamp(),
  source_version text NOT NULL DEFAULT 'OBSERVATION_PARITY_V1',
  UNIQUE(admission_id,source_signal_id,candidate_code)
);
CREATE INDEX IF NOT EXISTS observation_parity_candidate_v1_idx
ON analytics.observation_parity_v1(admission_id,verdict_code,checked_at DESC);
INSERT INTO analytics.system_job_schedule_v1(
 job_code,executor_code,enabled,timezone_code,weekdays,window_start,window_end,
 interval_minutes,timeout_seconds,priority,config_version)
VALUES('OBSERVATION_PARITY_REPLAY','OBSERVATION_PARITY_REPLAY_V1',true,'Europe/Moscow',
 '[0,1,2,3,4,5,6]'::jsonb,'00:00','23:59',5,90,1,'OBSERVATION_PARITY_V1')
ON CONFLICT(job_code) DO UPDATE SET executor_code=excluded.executor_code,
 enabled=true,interval_minutes=excluded.interval_minutes,timeout_seconds=excluded.timeout_seconds,
 priority=excluded.priority,config_version=excluded.config_version,updated_at=clock_timestamp();
GRANT SELECT,INSERT,UPDATE ON analytics.observation_parity_v1 TO alex,finam;
GRANT SELECT ON analytics.observation_parity_v1 TO finam_user;
GRANT USAGE,SELECT ON SEQUENCE analytics.observation_parity_v1_parity_id_seq TO alex,finam;
COMMIT;
