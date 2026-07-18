BEGIN;
CREATE TABLE IF NOT EXISTS analytics.swing_future_data_readiness_v1(
 readiness_id bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
 monitor_run_id uuid NOT NULL,
 plan_item_id uuid NOT NULL REFERENCES analytics.swing_next_research_plan_item_v1(plan_item_id),
 accumulated_bars integer NOT NULL,
 required_bars integer NOT NULL,
 remaining_bars integer NOT NULL,
 latest_bar_ts timestamptz,
 source_age_hours numeric,
 readiness_status text NOT NULL CHECK(readiness_status IN ('WAITING','READY','STALE','NO_SOURCE')),
 estimated_ready_at timestamptz,
 reason_code text NOT NULL,
 observed_at timestamptz NOT NULL DEFAULT clock_timestamp()
);
ALTER TABLE analytics.swing_future_data_readiness_v1 ADD COLUMN IF NOT EXISTS monitor_run_id uuid;
UPDATE analytics.swing_future_data_readiness_v1 SET monitor_run_id=gen_random_uuid() WHERE monitor_run_id IS NULL;
ALTER TABLE analytics.swing_future_data_readiness_v1 ALTER COLUMN monitor_run_id SET NOT NULL;
CREATE INDEX IF NOT EXISTS swing_future_data_readiness_latest_v1
 ON analytics.swing_future_data_readiness_v1(plan_item_id,observed_at DESC);
GRANT SELECT,INSERT ON analytics.swing_future_data_readiness_v1 TO alex;
GRANT USAGE,SELECT ON SEQUENCE analytics.swing_future_data_readiness_v1_readiness_id_seq TO alex;
COMMIT;
