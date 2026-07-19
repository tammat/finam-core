BEGIN;

CREATE TABLE IF NOT EXISTS analytics.research_entry_profile_v2 (
    asset_class text NOT NULL,
    timeframe text NOT NULL,
    entry_policy jsonb NOT NULL CHECK(jsonb_typeof(entry_policy)='object'),
    enabled boolean NOT NULL DEFAULT true,
    config_version text NOT NULL,
    updated_at timestamptz NOT NULL DEFAULT clock_timestamp(),
    PRIMARY KEY(asset_class,timeframe)
);

INSERT INTO analytics.research_entry_profile_v2(asset_class,timeframe,entry_policy,config_version)
VALUES
 ('EQUITY','M5','{"entry_policy_code":"META_ENTRY_V2","entry_profile_code":"EQUITY_M5","entry_trend_mode":"WITH_TREND","entry_trend_lookback":20,"entry_volatility_lookback":10,"entry_min_volatility_bps":2,"entry_max_volatility_bps":120,"entry_volume_mode":"REQUIRE","entry_min_volume_ratio":1.0,"entry_min_volume_coverage":0.8,"entry_session_mode":"OBSERVE","entry_regime_mode":"OBSERVE"}','META_ENTRY_V2'),
 ('FUTURES','M5','{"entry_policy_code":"META_ENTRY_V2","entry_profile_code":"FUTURES_M5","entry_trend_mode":"WITH_TREND","entry_trend_lookback":20,"entry_volatility_lookback":10,"entry_min_volatility_bps":2,"entry_max_volatility_bps":180,"entry_volume_mode":"REQUIRE","entry_min_volume_ratio":0.8,"entry_min_volume_coverage":0.8,"entry_session_mode":"OBSERVE","entry_regime_mode":"OBSERVE"}','META_ENTRY_V2'),
 ('OTHER','M5','{"entry_policy_code":"META_ENTRY_V2","entry_profile_code":"OTHER_M5","entry_trend_mode":"WITH_TREND","entry_trend_lookback":20,"entry_volatility_lookback":10,"entry_min_volatility_bps":2,"entry_max_volatility_bps":800,"entry_volume_mode":"OBSERVE","entry_min_volume_ratio":0.8,"entry_min_volume_coverage":0.8,"entry_session_mode":"OBSERVE","entry_regime_mode":"OBSERVE"}','META_ENTRY_V2')
ON CONFLICT(asset_class,timeframe) DO UPDATE SET
 entry_policy=excluded.entry_policy,enabled=true,config_version=excluded.config_version,
 updated_at=clock_timestamp();

-- Historical baseline results remain immutable; future grids use the shared
-- contract without doubling the hourly workload.
UPDATE analytics.edge_search_algorithm_registry_v1 r
SET parameter_grid=(SELECT jsonb_agg(
        (item - 'entry_policy_code' - 'entry_profile_code' - 'entry_trend_lookback'
              - 'entry_volatility_lookback' - 'entry_min_volatility_bps'
              - 'entry_max_volatility_bps' - 'entry_min_volume_ratio')
        || '{"entry_policy_code":"META_ENTRY_V2","entry_profile_code":"AUTO_BY_MARKET"}'::jsonb
        ORDER BY ordinal)
    FROM jsonb_array_elements(r.parameter_grid) WITH ORDINALITY source(item,ordinal)),
    config_version='META_ENTRY_V2_ALL',updated_at=clock_timestamp()
WHERE r.enabled;

CREATE TABLE IF NOT EXISTS analytics.edge_diagnostic_funnel_definition_v1 (
    funnel_code text PRIMARY KEY,
    title_ru text NOT NULL,
    recommendation_code text NOT NULL,
    system_scenario_code text NOT NULL,
    display_order integer NOT NULL UNIQUE,
    enabled boolean NOT NULL DEFAULT true
);

INSERT INTO analytics.edge_diagnostic_funnel_definition_v1
 (funnel_code,title_ru,recommendation_code,system_scenario_code,display_order)
VALUES
 ('ENTRY','Вход','REFINE_ENTRY_CONTRACT','GENERATE_META_ENTRY_VARIANTS',10),
 ('EXIT','Выход','COMPARE_DYNAMIC_EXIT','GENERATE_DYNAMIC_EXIT_VARIANTS',20),
 ('SESSION','Сессии','FOCUS_PROFITABLE_SESSIONS','GENERATE_SESSION_SPECIFIC_VARIANTS',30),
 ('EXECUTION','Исполнение','REDUCE_EXECUTION_LOSS','GENERATE_EXECUTION_EFFICIENT_VARIANTS',40),
 ('RISK','Риск','REDUCE_DRAWDOWN','GENERATE_RISK_ADJUSTED_VARIANTS',50),
 ('PORTFOLIO','Портфель','INCREASE_PORTFOLIO_DIVERSIFICATION','GENERATE_LOW_CORRELATION_VARIANTS',60)
ON CONFLICT(funnel_code) DO UPDATE SET title_ru=excluded.title_ru,
 recommendation_code=excluded.recommendation_code,system_scenario_code=excluded.system_scenario_code,
 display_order=excluded.display_order,enabled=true;

CREATE TABLE IF NOT EXISTS analytics.edge_diagnostic_funnel_run_v1 (
    funnel_run_id uuid PRIMARY KEY,
    scenario_run_id uuid NOT NULL,
    search_run_id uuid NOT NULL,
    funnel_code text NOT NULL REFERENCES analytics.edge_diagnostic_funnel_definition_v1(funnel_code),
    input_count integer NOT NULL CHECK(input_count>=0),
    final_count integer NOT NULL CHECK(final_count BETWEEN 0 AND input_count),
    lost_count integer NOT NULL CHECK(lost_count>=0),
    bottleneck_stage text NOT NULL,
    recommendation_code text NOT NULL,
    status_code text NOT NULL CHECK(status_code IN ('PASS','BLOCKED','NO_INPUT')),
    created_at timestamptz NOT NULL DEFAULT clock_timestamp(),
    UNIQUE(search_run_id,funnel_code)
);

CREATE TABLE IF NOT EXISTS analytics.edge_diagnostic_funnel_stage_v1 (
    funnel_run_id uuid NOT NULL REFERENCES analytics.edge_diagnostic_funnel_run_v1(funnel_run_id),
    stage_order integer NOT NULL CHECK(stage_order>0),
    stage_code text NOT NULL,
    evaluated_count integer NOT NULL CHECK(evaluated_count>=0),
    passed_count integer NOT NULL CHECK(passed_count>=0),
    lost_count integer NOT NULL CHECK(lost_count>=0),
    PRIMARY KEY(funnel_run_id,stage_order)
);

UPDATE analytics.edge_search_scenario_step_v1
SET step_order=step_order+100 WHERE scenario_code='AUTONOMOUS_EDGE_SEARCH' AND step_order>=9;
INSERT INTO analytics.edge_search_scenario_step_v1
 (scenario_code,step_order,executor_code,title_ru,timeout_seconds,required,enabled)
VALUES('AUTONOMOUS_EDGE_SEARCH',9,'BUILD_DIAGNOSTIC_FUNNELS','Диагностические воронки',300,true,true)
ON CONFLICT(scenario_code,step_order) DO UPDATE SET executor_code=excluded.executor_code,
 title_ru=excluded.title_ru,timeout_seconds=excluded.timeout_seconds,required=true,enabled=true;
UPDATE analytics.edge_search_scenario_step_v1
SET step_order=step_order-99 WHERE scenario_code='AUTONOMOUS_EDGE_SEARCH' AND step_order>=109;

UPDATE analytics.edge_search_scenario_v1 SET
 result_policy=result_policy || '{"entry_policy":"META_ENTRY_V2","entry_profiles":"AUTO_BY_MARKET","diagnostic_funnels":["ENTRY","EXIT","SESSION","EXECUTION","RISK","PORTFOLIO"],"pass_gates":"unchanged"}'::jsonb,
 config_version='V6_META_ENTRY_DIAGNOSTIC_FUNNELS',updated_at=clock_timestamp()
WHERE scenario_code='AUTONOMOUS_EDGE_SEARCH';

GRANT SELECT ON analytics.research_entry_profile_v2,
 analytics.edge_diagnostic_funnel_definition_v1,
 analytics.edge_diagnostic_funnel_run_v1,
 analytics.edge_diagnostic_funnel_stage_v1 TO alex;
GRANT INSERT,UPDATE,DELETE ON analytics.edge_diagnostic_funnel_run_v1,
 analytics.edge_diagnostic_funnel_stage_v1 TO alex;

COMMIT;
