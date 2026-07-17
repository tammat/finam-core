BEGIN;

ALTER TABLE analytics.walkforward_edge_search_v3
ADD COLUMN IF NOT EXISTS methodology_evidence jsonb NOT NULL DEFAULT '{}'::jsonb;

CREATE TABLE IF NOT EXISTS analytics.edge_methodology_contract_v1 (
 contract_code text PRIMARY KEY,
 policy jsonb NOT NULL,
 policy_hash text NOT NULL,
 active boolean NOT NULL DEFAULT false,
 created_at timestamptz NOT NULL DEFAULT clock_timestamp()
);
INSERT INTO analytics.edge_methodology_contract_v1(contract_code,policy,policy_hash,active)
VALUES('METHODOLOGY_V1_STRICT',
 '{"sequence":["STATISTICAL_SIGNIFICANCE","PARAMETER_ROBUSTNESS","INDEPENDENT_HOLDOUT","REALISTIC_EXECUTION","CAPACITY","PORTFOLIO_CONTRIBUTION"],"max_fdr_q":0.10,"min_robust_neighbors":2,"neighbor_min_profit_factor":1.0,"neighbor_min_folds":3,"stress_cost_multiplier":1.5,"stress_min_profit_factor":1.0,"min_capacity_rub":500000,"max_portfolio_abs_correlation":0.75,"min_portfolio_overlap_days":20,"empty_portfolio_policy":"BASE_PORTFOLIO_ALLOWED","all_gates_required":true}'::jsonb,
 md5('{"sequence":["STATISTICAL_SIGNIFICANCE","PARAMETER_ROBUSTNESS","INDEPENDENT_HOLDOUT","REALISTIC_EXECUTION","CAPACITY","PORTFOLIO_CONTRIBUTION"],"max_fdr_q":0.10,"min_robust_neighbors":2,"neighbor_min_profit_factor":1.0,"neighbor_min_folds":3,"stress_cost_multiplier":1.5,"stress_min_profit_factor":1.0,"min_capacity_rub":500000,"max_portfolio_abs_correlation":0.75,"min_portfolio_overlap_days":20,"empty_portfolio_policy":"BASE_PORTFOLIO_ALLOWED","all_gates_required":true}'::jsonb::text),true)
ON CONFLICT(contract_code) DO NOTHING;
CREATE UNIQUE INDEX IF NOT EXISTS edge_methodology_one_active_contract_v1
ON analytics.edge_methodology_contract_v1(active) WHERE active;
CREATE OR REPLACE FUNCTION analytics.guard_edge_methodology_contract_v1()
RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN
  IF TG_OP='DELETE' THEN RAISE EXCEPTION 'EDGE_METHODOLOGY_CONTRACT_DELETE_FORBIDDEN'; END IF;
  IF NEW.contract_code IS DISTINCT FROM OLD.contract_code OR NEW.policy IS DISTINCT FROM OLD.policy
     OR NEW.policy_hash IS DISTINCT FROM OLD.policy_hash THEN
    RAISE EXCEPTION 'EDGE_METHODOLOGY_CONTRACT_IMMUTABLE';
  END IF;
  RETURN NEW;
END $$;
DROP TRIGGER IF EXISTS trg_guard_edge_methodology_contract_v1 ON analytics.edge_methodology_contract_v1;
CREATE TRIGGER trg_guard_edge_methodology_contract_v1 BEFORE UPDATE OR DELETE
ON analytics.edge_methodology_contract_v1 FOR EACH ROW
EXECUTE FUNCTION analytics.guard_edge_methodology_contract_v1();

CREATE TABLE IF NOT EXISTS analytics.edge_methodology_evaluation_v1 (
 evaluation_id uuid PRIMARY KEY,
 scenario_run_id uuid NOT NULL REFERENCES analytics.edge_search_scenario_run_v1(run_id),
 search_run_id uuid NOT NULL,
 result_id uuid NOT NULL REFERENCES analytics.walkforward_edge_search_v3(result_id),
 contract_code text NOT NULL REFERENCES analytics.edge_methodology_contract_v1(contract_code),
 algorithm_code text NOT NULL,
 strategy_code text NOT NULL,
 symbol text NOT NULL,
 timeframe text NOT NULL,
 parameter_core jsonb NOT NULL,
 parameter_hash text NOT NULL,
 statistical_pass boolean NOT NULL,
 robustness_pass boolean NOT NULL,
 holdout_pass boolean NOT NULL,
 execution_pass boolean NOT NULL,
 capacity_pass boolean NOT NULL,
 portfolio_pass boolean NOT NULL,
 fdr_q numeric NOT NULL,
 robust_neighbors integer NOT NULL,
 stressed_profit_factor numeric NOT NULL,
 capacity_rub numeric NOT NULL,
 portfolio_correlation numeric,
 evidence jsonb NOT NULL,
 reason_codes jsonb NOT NULL,
 verdict_code text NOT NULL CHECK(verdict_code IN ('PASS','FAIL')),
 promotion_allowed boolean NOT NULL DEFAULT false CHECK(promotion_allowed=false),
 created_at timestamptz NOT NULL DEFAULT clock_timestamp(),
 UNIQUE(scenario_run_id,result_id)
);
CREATE INDEX IF NOT EXISTS edge_methodology_eval_lookup_v1
ON analytics.edge_methodology_evaluation_v1(scenario_run_id,strategy_code,symbol,parameter_hash,verdict_code);

CREATE TABLE IF NOT EXISTS analytics.edge_holdout_consumption_v1 (
 consumption_id uuid PRIMARY KEY,
 evaluation_id uuid NOT NULL REFERENCES analytics.edge_methodology_evaluation_v1(evaluation_id),
 strategy_code text NOT NULL,symbol text NOT NULL,timeframe text NOT NULL,
 parameter_hash text NOT NULL,holdout_end timestamptz NOT NULL,
 consumed_at timestamptz NOT NULL DEFAULT clock_timestamp(),
 UNIQUE(strategy_code,symbol,timeframe,parameter_hash,holdout_end)
);

DO $$ BEGIN
 IF NOT EXISTS (SELECT 1 FROM analytics.edge_search_scenario_step_v1
                WHERE scenario_code='AUTONOMOUS_EDGE_SEARCH' AND executor_code='METHODOLOGY_GATE') THEN
   UPDATE analytics.edge_search_scenario_step_v1 SET step_order=step_order+100
   WHERE scenario_code='AUTONOMOUS_EDGE_SEARCH' AND step_order>=3;
   UPDATE analytics.edge_search_scenario_step_v1 SET step_order=step_order-99
   WHERE scenario_code='AUTONOMOUS_EDGE_SEARCH' AND step_order>=103;
 END IF;
END $$;
INSERT INTO analytics.edge_search_scenario_step_v1
(scenario_code,step_order,executor_code,title_ru,enabled,timeout_seconds,required)
VALUES('AUTONOMOUS_EDGE_SEARCH',3,'METHODOLOGY_GATE','Методологический контракт',true,600,true)
ON CONFLICT(scenario_code,step_order) DO UPDATE SET executor_code=EXCLUDED.executor_code,
 title_ru=EXCLUDED.title_ru,enabled=true,timeout_seconds=EXCLUDED.timeout_seconds,required=true;
UPDATE analytics.edge_search_scenario_v1 SET config_version='V4_METHODOLOGY_CONTRACT',updated_at=clock_timestamp()
WHERE scenario_code='AUTONOMOUS_EDGE_SEARCH';

GRANT SELECT ON analytics.edge_methodology_contract_v1 TO alex;
GRANT SELECT,INSERT,UPDATE ON analytics.edge_methodology_evaluation_v1,
 analytics.edge_holdout_consumption_v1 TO alex;
COMMIT;
