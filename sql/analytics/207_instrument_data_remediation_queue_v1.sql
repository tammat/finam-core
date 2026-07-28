BEGIN;

ALTER TABLE analytics.instrument_scout_queue_v1
  ADD COLUMN IF NOT EXISTS remediation_stage_code text,
  ADD COLUMN IF NOT EXISTS attempt_count integer NOT NULL DEFAULT 0,
  ADD COLUMN IF NOT EXISTS max_attempts integer NOT NULL DEFAULT 12,
  ADD COLUMN IF NOT EXISTS next_attempt_at timestamptz NOT NULL DEFAULT clock_timestamp(),
  ADD COLUMN IF NOT EXISTS lease_owner text,
  ADD COLUMN IF NOT EXISTS lease_expires_at timestamptz,
  ADD COLUMN IF NOT EXISTS last_error_code text,
  ADD COLUMN IF NOT EXISTS last_checked_at timestamptz,
  ADD COLUMN IF NOT EXISTS completed_at timestamptz;

CREATE INDEX IF NOT EXISTS instrument_scout_remediation_due_v1
ON analytics.instrument_scout_queue_v1(status_code,next_attempt_at,priority)
WHERE action_code IN ('VERIFY_SPEC','COLLECT_DATA','COLLECT_LIQUIDITY','MONITOR_ROLL');

CREATE OR REPLACE FUNCTION analytics.enqueue_instrument_data_remediation_v1(p_run_id uuid)
RETURNS integer LANGUAGE plpgsql AS $$
DECLARE inserted_count integer;
BEGIN
  INSERT INTO analytics.instrument_scout_queue_v1
    (queue_id,run_id,symbol,action_code,status_code,priority,evidence,remediation_stage_code)
  SELECT gen_random_uuid(),s.run_id,s.symbol,s.next_action_code,'PENDING',
         greatest(1,1000-s.category_rank),
         jsonb_build_object('source','AUTONOMOUS_INSTRUMENT_FUNNEL_V2',
           'category',s.category_code,'reasons',s.reason_codes,
           'bars',s.bars,'latest_ts',s.latest_ts,
           'remediation_rank',s.remediation_rank),
         s.funnel_stage_code
  FROM (
    SELECT r.*,
           row_number() OVER (
             PARTITION BY r.category_code,r.next_action_code
             ORDER BY r.bars DESC,r.market_score DESC,r.symbol
           ) AS remediation_rank
    FROM analytics.instrument_scout_result_v1 r
    WHERE r.run_id=p_run_id
      AND r.next_action_code IN ('VERIFY_SPEC','COLLECT_DATA','COLLECT_LIQUIDITY','MONITOR_ROLL')
  ) s
  WHERE s.run_id=p_run_id
    AND s.remediation_rank<=3
  ON CONFLICT(run_id,symbol,action_code) DO UPDATE SET
    priority=excluded.priority,evidence=excluded.evidence,
    remediation_stage_code=excluded.remediation_stage_code,
    updated_at=clock_timestamp()
  WHERE analytics.instrument_scout_queue_v1.status_code NOT IN ('COMPLETE','APPLIED');
  GET DIAGNOSTICS inserted_count=ROW_COUNT;
  RETURN inserted_count;
END $$;

CREATE OR REPLACE VIEW analytics.instrument_data_remediation_status_v1 AS
SELECT action_code,status_code,count(*) AS instruments,
       sum(attempt_count) AS attempts,
       count(*) FILTER (WHERE status_code IN ('COMPLETE','APPLIED')) AS completed,
       min(next_attempt_at) FILTER (WHERE status_code IN ('PENDING','RETRY')) AS next_attempt_at,
       max(last_checked_at) AS last_checked_at
FROM analytics.instrument_scout_queue_v1
WHERE action_code IN ('VERIFY_SPEC','COLLECT_DATA','COLLECT_LIQUIDITY','MONITOR_ROLL')
GROUP BY action_code,status_code;

INSERT INTO analytics.system_job_schedule_v1
(job_code,executor_code,enabled,timezone_code,weekdays,window_start,window_end,
 interval_minutes,timeout_seconds,priority,config_version)
VALUES('INSTRUMENT_DATA_REMEDIATION','INSTRUMENT_DATA_REMEDIATION_V1',true,
 'Europe/Moscow','[0,1,2,3,4,5,6]'::jsonb,time '00:10',time '23:55',10,240,18,'V1')
ON CONFLICT(job_code) DO UPDATE SET executor_code=excluded.executor_code,enabled=true,
 interval_minutes=excluded.interval_minutes,timeout_seconds=excluded.timeout_seconds,
 priority=excluded.priority,config_version=excluded.config_version,updated_at=clock_timestamp();

GRANT SELECT,INSERT,UPDATE ON analytics.instrument_scout_queue_v1 TO alex;
GRANT SELECT ON analytics.instrument_data_remediation_status_v1 TO alex;

COMMIT;
