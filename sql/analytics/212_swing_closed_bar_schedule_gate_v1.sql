BEGIN;

CREATE TABLE IF NOT EXISTS analytics.swing_closed_bar_schedule_policy_v1 (
    policy_code text PRIMARY KEY,
    enabled boolean NOT NULL DEFAULT true,
    timeframes jsonb NOT NULL DEFAULT '["H1","H4","D1"]'::jsonb,
    market_load_limit numeric NOT NULL DEFAULT 3.25,
    offhours_load_limit numeric NOT NULL DEFAULT 4.50,
    config_version text NOT NULL,
    updated_at timestamptz NOT NULL DEFAULT clock_timestamp()
);

CREATE TABLE IF NOT EXISTS analytics.swing_closed_bar_cycle_checkpoint_v1 (
    scope_code text PRIMARY KEY,
    status_code text NOT NULL,
    last_seen_bars jsonb NOT NULL DEFAULT '{}'::jsonb,
    observed_bars jsonb NOT NULL DEFAULT '{}'::jsonb,
    reason_code text NOT NULL,
    load_1m numeric,
    last_started_at timestamptz,
    last_finished_at timestamptz,
    heartbeat_at timestamptz NOT NULL DEFAULT clock_timestamp(),
    updated_at timestamptz NOT NULL DEFAULT clock_timestamp()
);

INSERT INTO analytics.swing_closed_bar_schedule_policy_v1(
    policy_code,enabled,timeframes,market_load_limit,offhours_load_limit,config_version)
VALUES('SWING_EDGE_SEARCH',true,'["H1","H4","D1"]',3.25,4.50,'SWING_CLOSED_BAR_GATE_V1')
ON CONFLICT(policy_code) DO UPDATE SET
    enabled=excluded.enabled,timeframes=excluded.timeframes,
    market_load_limit=excluded.market_load_limit,offhours_load_limit=excluded.offhours_load_limit,
    config_version=excluded.config_version,updated_at=clock_timestamp();

-- One-time cleanup for partial buckets written by the legacy aggregator.
-- The incremental builder below this migration no longer creates such rows.
DELETE FROM analytics.swing_market_bars_v1
WHERE (timeframe='H1' AND ts + interval '1 hour' > clock_timestamp())
   OR (timeframe='H4' AND ts + interval '4 hours' > clock_timestamp())
   OR (timeframe='D1' AND ts + interval '1 day' > clock_timestamp());

INSERT INTO analytics.swing_closed_bar_cycle_checkpoint_v1(
    scope_code,status_code,last_seen_bars,observed_bars,reason_code)
SELECT 'SWING_EDGE_SEARCH','WAITING_NEW_BAR',bars,bars,'BASELINE_INSTALLED'
FROM (
    SELECT jsonb_object_agg(timeframe,latest) AS bars
    FROM (
        SELECT timeframe,max(ts) AS latest
        FROM analytics.swing_market_bars_v1
        WHERE (timeframe='H1' AND ts + interval '1 hour' <= clock_timestamp())
           OR (timeframe='H4' AND ts + interval '4 hours' <= clock_timestamp())
           OR (timeframe='D1' AND ts + interval '1 day' <= clock_timestamp())
        GROUP BY timeframe
    ) s
) q
ON CONFLICT(scope_code) DO NOTHING;

UPDATE analytics.system_job_schedule_v1
SET executor_code='SWING_CLOSED_BAR_SEARCH_V1', config_version='SWING_CLOSED_BAR_GATE_V1', updated_at=clock_timestamp()
WHERE job_code IN ('SWING_EDGE_SEARCH_NIGHT','SWING_EDGE_SEARCH_WEEKEND');

GRANT SELECT ON analytics.swing_closed_bar_schedule_policy_v1 TO alex;
GRANT SELECT,INSERT,UPDATE ON analytics.swing_closed_bar_cycle_checkpoint_v1 TO alex;

COMMIT;
