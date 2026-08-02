BEGIN;
CREATE TABLE IF NOT EXISTS analytics.marketcore_research_engine_snapshot_v1(
 snapshot_id bigserial PRIMARY KEY,
 checked_at timestamptz NOT NULL DEFAULT clock_timestamp(),
 engine_status text NOT NULL CHECK(engine_status IN ('COLLECTING','PASS','FAIL','BLOCKED','IDLE')),
 frozen_candidates integer NOT NULL,
 v5_collecting integer NOT NULL,
 v5_pass integer NOT NULL,
 v5_fail integer NOT NULL,
 spec_match integer NOT NULL,
 spec_mismatch integer NOT NULL,
 spec_not_proven integer NOT NULL,
 observation_match integer NOT NULL,
 observation_mismatch integer NOT NULL,
 observation_not_proven integer NOT NULL,
 swing_candidates integer NOT NULL,
 swing_match integer NOT NULL,
 swing_mismatch integer NOT NULL,
 swing_not_proven integer NOT NULL,
 active_paper_profiles integer NOT NULL,
 details jsonb NOT NULL,
 source_version text NOT NULL DEFAULT 'MARKETCORE_RESEARCH_ENGINE_V1'
);
INSERT INTO analytics.system_job_schedule_v1(
 job_code,executor_code,enabled,timezone_code,weekdays,window_start,window_end,
 interval_minutes,timeout_seconds,priority,config_version)
VALUES('MARKETCORE_RESEARCH_ENGINE','MARKETCORE_RESEARCH_ENGINE_V1',true,'Europe/Moscow',
 '[0,1,2,3,4,5,6]'::jsonb,'00:00','23:59',10,240,1,'MARKETCORE_RESEARCH_ENGINE_V1')
ON CONFLICT(job_code) DO UPDATE SET executor_code=excluded.executor_code,enabled=true,
 interval_minutes=excluded.interval_minutes,timeout_seconds=excluded.timeout_seconds,
 priority=excluded.priority,config_version=excluded.config_version,updated_at=clock_timestamp();
GRANT SELECT,INSERT ON analytics.marketcore_research_engine_snapshot_v1 TO alex,finam;
GRANT SELECT ON analytics.marketcore_research_engine_snapshot_v1 TO finam_user;
GRANT USAGE,SELECT ON SEQUENCE analytics.marketcore_research_engine_snapshot_v1_snapshot_id_seq TO alex,finam;
COMMIT;
