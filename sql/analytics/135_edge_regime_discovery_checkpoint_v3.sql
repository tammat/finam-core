BEGIN;

ALTER TABLE analytics.edge_regime_hypothesis_result_v2
    ADD COLUMN IF NOT EXISTS discovery_task_id uuid;

CREATE UNIQUE INDEX IF NOT EXISTS edge_regime_hypothesis_result_v2_task_regime_uq
ON analytics.edge_regime_hypothesis_result_v2(discovery_task_id,regime_code)
WHERE discovery_task_id IS NOT NULL;

CREATE TABLE IF NOT EXISTS analytics.edge_regime_discovery_run_v3(
    discovery_run_id uuid PRIMARY KEY,
    scenario_run_id uuid,
    status_code text NOT NULL CHECK(status_code IN ('RUNNING','COMPLETE','FAILED')),
    source_version text NOT NULL,
    data_cutoff_ts timestamptz NOT NULL,
    markets_total integer NOT NULL DEFAULT 0 CHECK(markets_total >= 0),
    tasks_total integer NOT NULL DEFAULT 0 CHECK(tasks_total >= 0),
    tasks_completed integer NOT NULL DEFAULT 0 CHECK(tasks_completed >= 0),
    results_total integer NOT NULL DEFAULT 0 CHECK(results_total >= 0),
    oos_pass integer NOT NULL DEFAULT 0 CHECK(oos_pass >= 0),
    progress_pct integer NOT NULL DEFAULT 0 CHECK(progress_pct BETWEEN 0 AND 100),
    started_at timestamptz NOT NULL DEFAULT clock_timestamp(),
    heartbeat_at timestamptz NOT NULL DEFAULT clock_timestamp(),
    finished_at timestamptz,
    error_text text
);

CREATE TABLE IF NOT EXISTS analytics.edge_regime_discovery_task_v3(
    task_id uuid PRIMARY KEY,
    discovery_run_id uuid NOT NULL REFERENCES analytics.edge_regime_discovery_run_v3(discovery_run_id) ON DELETE CASCADE,
    task_order integer NOT NULL CHECK(task_order > 0),
    symbol text NOT NULL,
    timeframe text NOT NULL,
    strategy_family text NOT NULL,
    strategy_code text NOT NULL,
    market_spec jsonb NOT NULL,
    configuration_spec jsonb NOT NULL,
    base_params jsonb NOT NULL,
    status_code text NOT NULL DEFAULT 'PENDING' CHECK(status_code IN ('PENDING','RUNNING','COMPLETE','FAILED')),
    attempts integer NOT NULL DEFAULT 0 CHECK(attempts >= 0),
    results_written integer NOT NULL DEFAULT 0 CHECK(results_written >= 0),
    pass_count integer NOT NULL DEFAULT 0 CHECK(pass_count >= 0),
    started_at timestamptz,
    heartbeat_at timestamptz,
    finished_at timestamptz,
    error_text text,
    UNIQUE(discovery_run_id,task_order)
);

CREATE INDEX IF NOT EXISTS edge_regime_discovery_task_v3_pending_idx
ON analytics.edge_regime_discovery_task_v3(discovery_run_id,status_code,task_order);

GRANT SELECT,INSERT,UPDATE ON analytics.edge_regime_discovery_run_v3 TO alex,finam;
GRANT SELECT,INSERT,UPDATE,DELETE ON analytics.edge_regime_discovery_task_v3 TO alex,finam;

COMMIT;
