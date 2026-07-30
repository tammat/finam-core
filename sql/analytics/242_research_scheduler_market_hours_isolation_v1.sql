BEGIN;

CREATE TABLE IF NOT EXISTS analytics.system_job_schedule_change_audit_v1 (
    changed_at timestamptz NOT NULL,
    job_code text NOT NULL,
    previous_schedule jsonb NOT NULL,
    new_schedule jsonb NOT NULL,
    reason_code text NOT NULL
);

INSERT INTO analytics.system_job_schedule_change_audit_v1
SELECT clock_timestamp(),job_code,
       jsonb_build_object('interval_minutes',30,'window_start','06:50:00',
                          'window_end','23:50:00','timeout_seconds',1800),
       jsonb_build_object('interval_minutes',60,'window_start','00:10:00',
                          'window_end','06:00:00','timeout_seconds',timeout_seconds),
       'ISOLATE_CPU_HEAVY_EDGE_RESEARCH_FROM_MARKET_HOURS'
FROM analytics.system_job_schedule_v1
WHERE job_code='SESSION_EXECUTION_EDGE_MICROSTRUCTURE_V2'
  AND NOT EXISTS (
      SELECT 1 FROM analytics.system_job_schedule_change_audit_v1 a
      WHERE a.job_code='SESSION_EXECUTION_EDGE_MICROSTRUCTURE_V2'
        AND a.reason_code='ISOLATE_CPU_HEAVY_EDGE_RESEARCH_FROM_MARKET_HOURS'
  );

UPDATE analytics.system_job_schedule_v1
SET interval_minutes=60,window_start=time '00:10:00',window_end=time '06:00:00',
    updated_at=clock_timestamp()
WHERE job_code='SESSION_EXECUTION_EDGE_MICROSTRUCTURE_V2';

GRANT SELECT ON analytics.system_job_schedule_change_audit_v1 TO alex,finam;

COMMIT;
