BEGIN;

CREATE TABLE IF NOT EXISTS analytics.edge_search_adaptive_scenario_v1 (
    adaptive_scenario_id UUID PRIMARY KEY,
    parent_run_id UUID NOT NULL,
    parent_search_run_id UUID NOT NULL,
    parent_result_id UUID NOT NULL,
    algorithm_code TEXT NOT NULL,
    strategy_code TEXT NOT NULL,
    target_symbol TEXT NOT NULL,
    parameter_grid JSONB NOT NULL CHECK (jsonb_typeof(parameter_grid)='array'),
    selection_metrics JSONB NOT NULL,
    generation_policy JSONB NOT NULL,
    holdout_policy JSONB NOT NULL,
    confirmation_after_ts TIMESTAMPTZ NOT NULL,
    minimum_future_bars INTEGER NOT NULL CHECK (minimum_future_bars >= 100),
    status_code TEXT NOT NULL CHECK (status_code IN (
      'WAITING_FUTURE_DATA','ACTIVE','EVALUATED_PASS','EVALUATED_FAIL','REJECTED'
    )),
    reason_code TEXT NOT NULL,
    config_version TEXT NOT NULL,
    activated_at TIMESTAMPTZ,
    evaluated_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL DEFAULT clock_timestamp(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT clock_timestamp(),
    UNIQUE (parent_result_id,config_version)
);

CREATE INDEX IF NOT EXISTS edge_search_adaptive_scenario_status_idx
ON analytics.edge_search_adaptive_scenario_v1(status_code,confirmation_after_ts);

INSERT INTO analytics.edge_search_scenario_step_v1
 (scenario_code,step_order,executor_code,title_ru,enabled,timeout_seconds,required)
VALUES ('AUTONOMOUS_EDGE_SEARCH',12,'GENERATE_ADAPTIVE_SCENARIOS',
        'Формирование дочерних сценариев',TRUE,300,TRUE)
ON CONFLICT (scenario_code,step_order) DO UPDATE SET
 executor_code=EXCLUDED.executor_code,title_ru=EXCLUDED.title_ru,enabled=TRUE,
 timeout_seconds=EXCLUDED.timeout_seconds,required=TRUE;

GRANT SELECT,INSERT,UPDATE ON analytics.edge_search_adaptive_scenario_v1 TO alex;
COMMIT;
