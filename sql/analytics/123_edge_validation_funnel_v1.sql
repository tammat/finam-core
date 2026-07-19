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

CREATE TABLE IF NOT EXISTS analytics.edge_strategy_degradation_policy_v1 (
    policy_code text PRIMARY KEY,
    min_variants integer NOT NULL CHECK(min_variants > 0),
    min_oos_retention numeric NOT NULL CHECK(min_oos_retention BETWEEN 0 AND 1),
    min_cost_retention numeric NOT NULL CHECK(min_cost_retention BETWEEN 0 AND 1),
    min_stability_retention numeric NOT NULL CHECK(min_stability_retention BETWEEN 0 AND 1),
    quarantine_after_cycles integer NOT NULL CHECK(quarantine_after_cycles >= 2),
    active boolean NOT NULL DEFAULT false,
    created_at timestamptz NOT NULL DEFAULT clock_timestamp()
);

INSERT INTO analytics.edge_strategy_degradation_policy_v1
    (policy_code,min_variants,min_oos_retention,min_cost_retention,
     min_stability_retention,quarantine_after_cycles,active)
VALUES ('EDGE_STRATEGY_DEGRADATION_V1',20,0.20,0.50,0.50,3,true)
ON CONFLICT(policy_code) DO UPDATE SET
    min_variants=EXCLUDED.min_variants,min_oos_retention=EXCLUDED.min_oos_retention,
    min_cost_retention=EXCLUDED.min_cost_retention,
    min_stability_retention=EXCLUDED.min_stability_retention,
    quarantine_after_cycles=EXCLUDED.quarantine_after_cycles,active=true;

CREATE UNIQUE INDEX IF NOT EXISTS edge_strategy_degradation_one_active_v1
    ON analytics.edge_strategy_degradation_policy_v1(active) WHERE active;

CREATE TABLE IF NOT EXISTS analytics.edge_strategy_degradation_v1 (
    evaluation_id uuid PRIMARY KEY,
    search_run_id uuid NOT NULL,
    strategy_code text NOT NULL,
    strategy_family text NOT NULL,
    symbol text NOT NULL,
    total_variants integer NOT NULL,
    in_sample_pass integer NOT NULL,
    oos_pass integer NOT NULL,
    after_costs_pass integer NOT NULL,
    stable_pass integer NOT NULL,
    oos_retention numeric NOT NULL,
    cost_retention numeric NOT NULL,
    stability_retention numeric NOT NULL,
    consecutive_degraded_cycles integer NOT NULL,
    degradation_code text NOT NULL CHECK(degradation_code IN
        ('HEALTHY','NO_IN_SAMPLE_EDGE','OOS_COLLAPSE','COST_EROSION','UNSTABLE','NO_STABLE_PASS')),
    promotion_blocked boolean NOT NULL,
    research_quarantine_required boolean NOT NULL,
    block_scope text NOT NULL CHECK(block_scope='STRATEGY_VERSION_RESEARCH'),
    policy_code text NOT NULL REFERENCES analytics.edge_strategy_degradation_policy_v1(policy_code),
    created_at timestamptz NOT NULL DEFAULT clock_timestamp(),
    UNIQUE(search_run_id,strategy_code,symbol)
);

CREATE INDEX IF NOT EXISTS edge_strategy_degradation_latest_v1
    ON analytics.edge_strategy_degradation_v1(strategy_code,symbol,created_at DESC);

GRANT SELECT ON analytics.edge_validation_funnel_remediation_v1,
    analytics.edge_validation_funnel_analysis_v1,
    analytics.edge_strategy_degradation_policy_v1,
    analytics.edge_strategy_degradation_v1 TO alex;
GRANT INSERT,UPDATE ON analytics.edge_validation_funnel_analysis_v1,
    analytics.edge_strategy_degradation_v1 TO alex;

COMMIT;
