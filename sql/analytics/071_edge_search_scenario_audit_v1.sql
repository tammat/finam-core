BEGIN;

CREATE TABLE IF NOT EXISTS analytics.edge_search_algorithm_registry_v1 (
    algorithm_code TEXT PRIMARY KEY,
    strategy_code TEXT NOT NULL,
    enabled BOOLEAN NOT NULL DEFAULT TRUE,
    parameter_grid JSONB NOT NULL CHECK (jsonb_typeof(parameter_grid)='array'),
    regime_policy JSONB NOT NULL DEFAULT '{}'::jsonb,
    gate_policy JSONB NOT NULL DEFAULT '{}'::jsonb,
    config_version TEXT NOT NULL,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT clock_timestamp()
);

CREATE TABLE IF NOT EXISTS analytics.edge_search_scenario_v1 (
    scenario_code TEXT PRIMARY KEY,
    title_ru TEXT NOT NULL,
    enabled BOOLEAN NOT NULL DEFAULT TRUE,
    schedule_policy JSONB NOT NULL,
    result_policy JSONB NOT NULL,
    config_version TEXT NOT NULL,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT clock_timestamp()
);

CREATE TABLE IF NOT EXISTS analytics.edge_search_scenario_step_v1 (
    scenario_code TEXT NOT NULL REFERENCES analytics.edge_search_scenario_v1(scenario_code),
    step_order INTEGER NOT NULL CHECK (step_order > 0),
    executor_code TEXT NOT NULL,
    title_ru TEXT NOT NULL,
    enabled BOOLEAN NOT NULL DEFAULT TRUE,
    timeout_seconds INTEGER NOT NULL DEFAULT 1800 CHECK (timeout_seconds BETWEEN 1 AND 7200),
    required BOOLEAN NOT NULL DEFAULT TRUE,
    PRIMARY KEY (scenario_code, step_order),
    UNIQUE (scenario_code, executor_code)
);

CREATE TABLE IF NOT EXISTS analytics.edge_search_scenario_run_v1 (
    run_id UUID PRIMARY KEY,
    cycle_id UUID NOT NULL REFERENCES analytics.edge_search_cycle_status_v1(cycle_id),
    scenario_code TEXT NOT NULL REFERENCES analytics.edge_search_scenario_v1(scenario_code),
    status_code TEXT NOT NULL CHECK (status_code IN ('RUNNING','SUCCEEDED','FAILED','SKIPPED')),
    config_snapshot JSONB NOT NULL,
    started_at TIMESTAMPTZ NOT NULL DEFAULT clock_timestamp(),
    finished_at TIMESTAMPTZ
);

CREATE TABLE IF NOT EXISTS analytics.edge_search_step_run_v1 (
    step_run_id UUID PRIMARY KEY,
    run_id UUID NOT NULL REFERENCES analytics.edge_search_scenario_run_v1(run_id),
    step_order INTEGER NOT NULL,
    executor_code TEXT NOT NULL,
    status_code TEXT NOT NULL CHECK (status_code IN ('RUNNING','SUCCEEDED','FAILED','SKIPPED')),
    started_at TIMESTAMPTZ NOT NULL DEFAULT clock_timestamp(),
    finished_at TIMESTAMPTZ,
    duration_ms BIGINT,
    return_code INTEGER,
    metrics JSONB NOT NULL DEFAULT '{}'::jsonb,
    stdout_tail TEXT,
    stderr_tail TEXT,
    UNIQUE (run_id, step_order)
);

CREATE TABLE IF NOT EXISTS analytics.edge_search_run_analysis_v1 (
    run_id UUID PRIMARY KEY REFERENCES analytics.edge_search_scenario_run_v1(run_id),
    outcome_code TEXT NOT NULL,
    primary_reason_code TEXT NOT NULL,
    success_factors JSONB NOT NULL DEFAULT '[]'::jsonb,
    failure_factors JSONB NOT NULL DEFAULT '[]'::jsonb,
    evidence JSONB NOT NULL DEFAULT '{}'::jsonb,
    recommendation_code TEXT NOT NULL,
    explanation_ru TEXT NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT clock_timestamp()
);

INSERT INTO analytics.edge_search_scenario_v1
    (scenario_code,title_ru,enabled,schedule_policy,result_policy,config_version)
VALUES ('AUTONOMOUS_EDGE_SEARCH','Автономный поиск подтверждённого преимущества',TRUE,
        '{"owner":"system","trigger":"schedule_or_db_command","manual_algorithm_start":false}'::jsonb,
        '{"persist_steps":true,"persist_outputs":true,"analyze_outcome":true}'::jsonb,'V1')
ON CONFLICT (scenario_code) DO UPDATE SET
    title_ru=EXCLUDED.title_ru, schedule_policy=EXCLUDED.schedule_policy,
    result_policy=EXCLUDED.result_policy, config_version=EXCLUDED.config_version,
    updated_at=clock_timestamp();

INSERT INTO analytics.edge_search_scenario_step_v1
    (scenario_code,step_order,executor_code,title_ru)
VALUES
 ('AUTONOMOUS_EDGE_SEARCH',1,'DISCOVER_REGIME','Поиск режимных гипотез'),
 ('AUTONOMOUS_EDGE_SEARCH',2,'WALKFORWARD','Пошаговая проверка'),
 ('AUTONOMOUS_EDGE_SEARCH',3,'PROMOTE_OOS','Продвижение подтверждённых OOS'),
 ('AUTONOMOUS_EDGE_SEARCH',4,'VALIDATE_EDGE','Подтверждение преимущества'),
 ('AUTONOMOUS_EDGE_SEARCH',5,'OOS_FORWARD_HANDOFF','Передача OOS в Forward'),
 ('AUTONOMOUS_EDGE_SEARCH',6,'ADMIT_FORWARD','Допуск чистой Forward-когорты'),
 ('AUTONOMOUS_EDGE_SEARCH',7,'OBSERVE_FORWARD','Forward-наблюдение'),
 ('AUTONOMOUS_EDGE_SEARCH',8,'PROJECT_SHADOW','Проекция теневых сделок'),
 ('AUTONOMOUS_EDGE_SEARCH',9,'ADMIT_PAPER','Допуск Paper'),
 ('AUTONOMOUS_EDGE_SEARCH',10,'BUILD_LINEAGE','Построение аудиторской цепочки')
ON CONFLICT (scenario_code,step_order) DO UPDATE SET
 executor_code=EXCLUDED.executor_code,title_ru=EXCLUDED.title_ru;

INSERT INTO analytics.edge_search_algorithm_registry_v1
    (algorithm_code,strategy_code,parameter_grid,regime_policy,gate_policy,config_version)
VALUES
 ('MOMENTUM','MOMENTUM_CONTINUATION_V1','[]','{"mode":"contract_aware"}','{"decision":"PASS_required"}','V1'),
 ('BREAKOUT','BREAKOUT_V1','[]','{"mode":"contract_aware"}','{"decision":"PASS_required"}','V1'),
 ('RSI','RSI_MEAN_REVERSION_V1','[]','{"mode":"contract_aware"}','{"decision":"PASS_required"}','V1'),
 ('VWAP','VWAP_REVERSION_V2','[]','{"mode":"contract_aware"}','{"decision":"PASS_required"}','V1'),
 ('BOLLINGER','BOLLINGER_REVERSION_V1','[]','{"mode":"contract_aware"}','{"decision":"PASS_required"}','V1')
ON CONFLICT (algorithm_code) DO UPDATE SET
 strategy_code=EXCLUDED.strategy_code,regime_policy=EXCLUDED.regime_policy,
 gate_policy=EXCLUDED.gate_policy,config_version=EXCLUDED.config_version,
 updated_at=clock_timestamp();

GRANT SELECT ON analytics.edge_search_algorithm_registry_v1,
 analytics.edge_search_scenario_v1,analytics.edge_search_scenario_step_v1 TO alex;
GRANT SELECT,INSERT,UPDATE ON analytics.edge_search_scenario_run_v1,
 analytics.edge_search_step_run_v1,analytics.edge_search_run_analysis_v1 TO alex;
COMMIT;
