BEGIN;
CREATE TABLE IF NOT EXISTS analytics.swing_parity_v1(
 process_id uuid PRIMARY KEY,
 research_spec jsonb NOT NULL,
 research_spec_hash text NOT NULL,
 runtime_spec jsonb,
 runtime_spec_hash text,
 spec_verdict text NOT NULL CHECK(spec_verdict IN ('MATCH','MISMATCH','NOT_PROVEN')),
 observation_match integer NOT NULL DEFAULT 0,
 observation_mismatch integer NOT NULL DEFAULT 0,
 observation_not_proven integer NOT NULL DEFAULT 0,
 reason_codes jsonb NOT NULL DEFAULT '[]'::jsonb,
 checked_at timestamptz NOT NULL DEFAULT clock_timestamp(),
 source_version text NOT NULL DEFAULT 'SWING_PARITY_V1'
);
INSERT INTO analytics.system_job_schedule_v1(
 job_code,executor_code,enabled,timezone_code,weekdays,window_start,window_end,
 interval_minutes,timeout_seconds,priority,config_version)
VALUES('SWING_PARITY_REPLAY','SWING_PARITY_REPLAY_V1',true,'Europe/Moscow',
 '[0,1,2,3,4,5,6]'::jsonb,'00:00','23:59',5,90,1,'SWING_PARITY_V1')
ON CONFLICT(job_code) DO UPDATE SET executor_code=excluded.executor_code,enabled=true,
 interval_minutes=excluded.interval_minutes,timeout_seconds=excluded.timeout_seconds,
 priority=excluded.priority,config_version=excluded.config_version,updated_at=clock_timestamp();
GRANT SELECT,INSERT,UPDATE ON analytics.swing_parity_v1 TO alex,finam;
GRANT SELECT ON analytics.swing_parity_v1 TO finam_user;
COMMIT;
