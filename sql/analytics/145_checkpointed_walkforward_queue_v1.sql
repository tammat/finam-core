BEGIN;

CREATE TABLE IF NOT EXISTS analytics.walkforward_campaign_v4(
 campaign_id uuid PRIMARY KEY,
 scenario_run_id uuid,
 status_code text NOT NULL DEFAULT 'RUNNING' CHECK(status_code IN ('RUNNING','COMPLETE','FAILED')),
 phase_code text NOT NULL DEFAULT 'COARSE' CHECK(phase_code IN ('COARSE','FULL_OOS','COMPLETE')),
 data_cutoff_ts timestamptz NOT NULL,
 top_share numeric NOT NULL DEFAULT .10 CHECK(top_share BETWEEN .05 AND .10),
 cpu_limit integer NOT NULL DEFAULT 2 CHECK(cpu_limit BETWEEN 1 AND 2),
 tasks_total integer NOT NULL DEFAULT 0,
 tasks_complete integer NOT NULL DEFAULT 0,
 progress_pct integer NOT NULL DEFAULT 0 CHECK(progress_pct BETWEEN 0 AND 100),
 started_at timestamptz NOT NULL DEFAULT clock_timestamp(),
 heartbeat_at timestamptz NOT NULL DEFAULT clock_timestamp(),
 finished_at timestamptz,
 error_text text
);

CREATE TABLE IF NOT EXISTS analytics.walkforward_algorithm_task_v4(
 algorithm_task_id uuid PRIMARY KEY,
 campaign_id uuid NOT NULL REFERENCES analytics.walkforward_campaign_v4(campaign_id) ON DELETE CASCADE,
 algorithm_code text NOT NULL,
 priority_rank integer NOT NULL,
 status_code text NOT NULL DEFAULT 'PENDING' CHECK(status_code IN ('PENDING','RUNNING','COMPLETE','FAILED')),
 variants_total integer NOT NULL DEFAULT 0,
 variants_complete integer NOT NULL DEFAULT 0,
 heartbeat_at timestamptz,
 error_text text,
 UNIQUE(campaign_id,algorithm_code)
);

CREATE TABLE IF NOT EXISTS analytics.walkforward_variant_task_v4(
 variant_task_id uuid PRIMARY KEY,
 algorithm_task_id uuid NOT NULL REFERENCES analytics.walkforward_algorithm_task_v4(algorithm_task_id) ON DELETE CASCADE,
 symbol text NOT NULL,timeframe text NOT NULL,strategy_code text NOT NULL,
 parameter_json jsonb NOT NULL,parameter_hash text NOT NULL,
 phase_code text NOT NULL DEFAULT 'COARSE' CHECK(phase_code IN ('COARSE','FULL_OOS','REJECTED')),
 coarse_score numeric,
 status_code text NOT NULL DEFAULT 'PENDING' CHECK(status_code IN ('PENDING','RUNNING','COMPLETE','REJECTED','FAILED')),
 rejection_code text,
 created_at timestamptz NOT NULL DEFAULT clock_timestamp(),
 heartbeat_at timestamptz,
 UNIQUE(algorithm_task_id,symbol,timeframe,parameter_hash)
);

CREATE TABLE IF NOT EXISTS analytics.walkforward_fold_checkpoint_v4(
 variant_task_id uuid NOT NULL REFERENCES analytics.walkforward_variant_task_v4(variant_task_id) ON DELETE CASCADE,
 fold_no integer NOT NULL CHECK(fold_no BETWEEN 0 AND 5),
 status_code text NOT NULL DEFAULT 'PENDING' CHECK(status_code IN ('PENDING','RUNNING','COMPLETE','FAILED')),
 metrics jsonb NOT NULL DEFAULT '{}'::jsonb,
 evidence jsonb NOT NULL DEFAULT '{}'::jsonb,
 started_at timestamptz,finished_at timestamptz,error_text text,
 PRIMARY KEY(variant_task_id,fold_no)
);

ALTER TABLE analytics.walkforward_fold_checkpoint_v4
 ADD COLUMN IF NOT EXISTS attempts integer NOT NULL DEFAULT 0 CHECK(attempts >= 0);

CREATE TABLE IF NOT EXISTS analytics.walkforward_feature_cache_v4(
 symbol text NOT NULL,timeframe text NOT NULL,data_cutoff_ts timestamptz NOT NULL,
 feature_version text NOT NULL,feature_payload jsonb NOT NULL,
 created_at timestamptz NOT NULL DEFAULT clock_timestamp(),
 PRIMARY KEY(symbol,timeframe,data_cutoff_ts,feature_version)
);

CREATE INDEX IF NOT EXISTS walkforward_variant_pending_v4_idx
 ON analytics.walkforward_variant_task_v4(status_code,phase_code,algorithm_task_id);
CREATE INDEX IF NOT EXISTS walkforward_fold_pending_v4_idx
 ON analytics.walkforward_fold_checkpoint_v4(status_code,variant_task_id,fold_no);

GRANT SELECT,INSERT,UPDATE ON analytics.walkforward_campaign_v4,
 analytics.walkforward_algorithm_task_v4,analytics.walkforward_variant_task_v4,
 analytics.walkforward_fold_checkpoint_v4,analytics.walkforward_feature_cache_v4 TO alex,finam;

COMMIT;
