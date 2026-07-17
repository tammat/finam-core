BEGIN;
CREATE TABLE IF NOT EXISTS analytics.edge_search_algorithm_analysis_v1 (
    run_id UUID NOT NULL REFERENCES analytics.edge_search_scenario_run_v1(run_id),
    search_run_id UUID NOT NULL,
    algorithm_code TEXT NOT NULL REFERENCES analytics.edge_search_algorithm_registry_v1(algorithm_code),
    verdict_code TEXT NOT NULL CHECK (verdict_code IN ('PASS','FAIL','NO_DATA')),
    candidates_evaluated INTEGER NOT NULL DEFAULT 0,
    passes INTEGER NOT NULL DEFAULT 0,
    primary_reason_code TEXT NOT NULL,
    reason_distribution JSONB NOT NULL DEFAULT '{}'::jsonb,
    best_metrics JSONB NOT NULL DEFAULT '{}'::jsonb,
    success_factors JSONB NOT NULL DEFAULT '[]'::jsonb,
    failure_factors JSONB NOT NULL DEFAULT '[]'::jsonb,
    recommendation_code TEXT NOT NULL,
    explanation_ru TEXT NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT clock_timestamp(),
    PRIMARY KEY (run_id,algorithm_code)
);

INSERT INTO analytics.edge_search_scenario_step_v1
 (scenario_code,step_order,executor_code,title_ru,enabled,timeout_seconds,required)
VALUES ('AUTONOMOUS_EDGE_SEARCH',11,'ANALYZE_RESULTS','Анализ причин по алгоритмам',TRUE,300,TRUE)
ON CONFLICT (scenario_code,step_order) DO UPDATE SET
 executor_code=EXCLUDED.executor_code,title_ru=EXCLUDED.title_ru,enabled=TRUE,
 timeout_seconds=EXCLUDED.timeout_seconds,required=TRUE;

GRANT SELECT,INSERT,UPDATE ON analytics.edge_search_algorithm_analysis_v1 TO alex;
COMMIT;
