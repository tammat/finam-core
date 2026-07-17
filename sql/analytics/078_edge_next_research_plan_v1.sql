BEGIN;

CREATE TABLE IF NOT EXISTS analytics.edge_next_research_plan_v1 (
    plan_id uuid PRIMARY KEY,
    parent_run_id uuid NOT NULL REFERENCES analytics.edge_search_scenario_run_v1(run_id),
    parent_search_run_id uuid NOT NULL,
    generator_version text NOT NULL,
    status_code text NOT NULL CHECK (status_code IN ('READY','WAITING_FUTURE_DATA','ACTIVE','EVALUATED','EMPTY')),
    source_failures integer NOT NULL DEFAULT 0 CHECK (source_failures >= 0),
    item_count integer NOT NULL DEFAULT 0 CHECK (item_count >= 0),
    total_parameter_variants integer NOT NULL DEFAULT 0 CHECK (total_parameter_variants >= 0),
    reason_summary jsonb NOT NULL DEFAULT '{}'::jsonb,
    created_at timestamptz NOT NULL DEFAULT clock_timestamp(),
    updated_at timestamptz NOT NULL DEFAULT clock_timestamp(),
    UNIQUE (parent_run_id, generator_version)
);

CREATE TABLE IF NOT EXISTS analytics.edge_next_research_plan_item_v1 (
    plan_item_id uuid PRIMARY KEY,
    plan_id uuid NOT NULL REFERENCES analytics.edge_next_research_plan_v1(plan_id),
    priority smallint NOT NULL CHECK (priority > 0),
    algorithm_code text NOT NULL REFERENCES analytics.edge_search_algorithm_registry_v1(algorithm_code),
    strategy_code text NOT NULL,
    primary_reason_code text NOT NULL,
    adaptation_code text NOT NULL,
    parameter_grid jsonb NOT NULL CHECK (jsonb_typeof(parameter_grid)='array'),
    regime_policy jsonb NOT NULL DEFAULT '{}'::jsonb,
    pass_gate_snapshot jsonb NOT NULL,
    pass_gate_hash text NOT NULL,
    evaluation_budget integer NOT NULL CHECK (evaluation_budget > 0),
    source_result_id uuid NOT NULL REFERENCES analytics.walkforward_edge_search_v3(result_id),
    adaptive_scenario_id uuid REFERENCES analytics.edge_search_adaptive_scenario_v1(adaptive_scenario_id),
    status_code text NOT NULL CHECK (status_code IN ('WAITING_FUTURE_DATA','ACTIVE','EVALUATED_PASS','EVALUATED_FAIL')),
    rationale_ru text NOT NULL,
    created_at timestamptz NOT NULL DEFAULT clock_timestamp(),
    updated_at timestamptz NOT NULL DEFAULT clock_timestamp(),
    UNIQUE (plan_id, algorithm_code),
    UNIQUE (plan_id, priority)
);

CREATE OR REPLACE FUNCTION analytics.guard_edge_plan_pass_gate_v1()
RETURNS trigger LANGUAGE plpgsql AS $$
DECLARE registry_gate jsonb;
BEGIN
  SELECT gate_policy INTO registry_gate
  FROM analytics.edge_search_algorithm_registry_v1
  WHERE algorithm_code=NEW.algorithm_code;
  IF TG_OP='INSERT' AND (registry_gate IS NULL OR NEW.pass_gate_snapshot IS DISTINCT FROM registry_gate) THEN
    RAISE EXCEPTION 'EDGE_PLAN_PASS_GATE_MISMATCH:%', NEW.algorithm_code;
  END IF;
  IF NEW.pass_gate_hash <> md5(NEW.pass_gate_snapshot::text) THEN
    RAISE EXCEPTION 'EDGE_PLAN_PASS_GATE_HASH_MISMATCH:%', NEW.algorithm_code;
  END IF;
  IF TG_OP='UPDATE' AND (NEW.pass_gate_snapshot IS DISTINCT FROM OLD.pass_gate_snapshot
      OR NEW.pass_gate_hash IS DISTINCT FROM OLD.pass_gate_hash) THEN
    RAISE EXCEPTION 'EDGE_PLAN_PASS_GATE_IMMUTABLE:%', NEW.algorithm_code;
  END IF;
  RETURN NEW;
END $$;

DROP TRIGGER IF EXISTS trg_guard_edge_plan_pass_gate_v1 ON analytics.edge_next_research_plan_item_v1;
CREATE TRIGGER trg_guard_edge_plan_pass_gate_v1
BEFORE INSERT OR UPDATE ON analytics.edge_next_research_plan_item_v1
FOR EACH ROW EXECUTE FUNCTION analytics.guard_edge_plan_pass_gate_v1();

CREATE INDEX IF NOT EXISTS idx_edge_next_plan_status_v1
ON analytics.edge_next_research_plan_v1(status_code,created_at DESC);
CREATE INDEX IF NOT EXISTS idx_edge_next_plan_item_status_v1
ON analytics.edge_next_research_plan_item_v1(status_code,priority);

GRANT SELECT,INSERT,UPDATE ON analytics.edge_next_research_plan_v1 TO alex;
GRANT SELECT,INSERT,UPDATE ON analytics.edge_next_research_plan_item_v1 TO alex;

COMMIT;
