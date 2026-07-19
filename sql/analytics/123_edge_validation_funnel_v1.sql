BEGIN;

ALTER TABLE analytics.walkforward_edge_search_v3
    ADD COLUMN IF NOT EXISTS in_sample_passed boolean,
    ADD COLUMN IF NOT EXISTS oos_gross_passed boolean,
    ADD COLUMN IF NOT EXISTS cost_adjusted_passed boolean,
    ADD COLUMN IF NOT EXISTS stability_passed boolean,
    ADD COLUMN IF NOT EXISTS validation_funnel jsonb NOT NULL DEFAULT '{}'::jsonb;

CREATE INDEX IF NOT EXISTS walkforward_edge_search_v3_funnel_v1
    ON analytics.walkforward_edge_search_v3(search_run_id, stability_passed)
    WHERE validation_funnel <> '{}'::jsonb;

CREATE TABLE IF NOT EXISTS analytics.edge_validation_funnel_remediation_v1 (
    stage_code text PRIMARY KEY,
    recommendation_code text NOT NULL UNIQUE,
    system_scenario_code text NOT NULL,
    priority integer NOT NULL CHECK(priority BETWEEN 1 AND 100),
    active boolean NOT NULL DEFAULT true
);

INSERT INTO analytics.edge_validation_funnel_remediation_v1
    (stage_code,recommendation_code,system_scenario_code,priority)
VALUES
    ('IN_SAMPLE','REFRAME_ENTRY','GENERATE_NEW_ENTRY_HYPOTHESES',100),
    ('OOS','REDUCE_OVERFIT','EXPAND_REGIMES_AND_REDUCE_PARAMETERS',90),
    ('AFTER_COSTS','REDUCE_TURNOVER','GENERATE_COST_EFFICIENT_VARIANTS',80),
    ('STABILITY','EXPAND_EVIDENCE','EXPAND_FOLDS_AND_REGIME_EVIDENCE',70)
ON CONFLICT(stage_code) DO UPDATE SET
    recommendation_code=EXCLUDED.recommendation_code,
    system_scenario_code=EXCLUDED.system_scenario_code,
    priority=EXCLUDED.priority,
    active=true;

CREATE TABLE IF NOT EXISTS analytics.edge_validation_funnel_analysis_v1 (
    search_run_id uuid PRIMARY KEY,
    total_variants integer NOT NULL CHECK(total_variants >= 0),
    in_sample_pass integer NOT NULL CHECK(in_sample_pass BETWEEN 0 AND total_variants),
    oos_pass integer NOT NULL CHECK(oos_pass BETWEEN 0 AND in_sample_pass),
    after_costs_pass integer NOT NULL CHECK(after_costs_pass BETWEEN 0 AND oos_pass),
    stable_pass integer NOT NULL CHECK(stable_pass BETWEEN 0 AND after_costs_pass),
    bottleneck_stage text NOT NULL REFERENCES analytics.edge_validation_funnel_remediation_v1(stage_code),
    lost_variants integer NOT NULL CHECK(lost_variants >= 0),
    recommendation_code text NOT NULL REFERENCES analytics.edge_validation_funnel_remediation_v1(recommendation_code),
    system_scenario_code text NOT NULL,
    created_at timestamptz NOT NULL DEFAULT clock_timestamp()
);

GRANT SELECT ON analytics.edge_validation_funnel_remediation_v1,
    analytics.edge_validation_funnel_analysis_v1 TO alex;
GRANT INSERT,UPDATE ON analytics.edge_validation_funnel_analysis_v1 TO alex;

COMMIT;
