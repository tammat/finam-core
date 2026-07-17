BEGIN;

CREATE TABLE IF NOT EXISTS analytics.edge_methodology_remediation_rule_v1 (
    gate_code text PRIMARY KEY,
    priority smallint NOT NULL CHECK(priority>0),
    adaptation_code text NOT NULL,
    mutation_scope jsonb NOT NULL,
    rationale_ru text NOT NULL,
    active boolean NOT NULL DEFAULT true,
    created_at timestamptz NOT NULL DEFAULT clock_timestamp(),
    CHECK (jsonb_typeof(mutation_scope)='array'),
    CHECK (NOT mutation_scope ?| ARRAY['pass_gate','methodology_contract','execution_costs','consumed_holdout'])
);

INSERT INTO analytics.edge_methodology_remediation_rule_v1
(gate_code,priority,adaptation_code,mutation_scope,rationale_ru) VALUES
('REALISTIC_EXECUTION',1,'STRENGTHEN_SIGNAL_SAME_COSTS','["parameters"]','Усилить сигнал при неизменной полной модели издержек.'),
('STATISTICAL_SIGNIFICANCE',2,'EXPAND_FUTURE_EVIDENCE','["parameters","future_window"]','Накопить больше независимых будущих наблюдений.'),
('PARAMETER_ROBUSTNESS',3,'LOCAL_PARAMETER_NEIGHBORHOOD','["parameters"]','Проверить соседние параметры вместо единичного пика.'),
('INDEPENDENT_HOLDOUT',4,'NEW_CLEAN_HOLDOUT','["future_window"]','Использовать только новую непотреблённую выборку.'),
('CAPACITY',5,'LIQUIDITY_PEER_MARKET','["target_market"]','Перенести гипотезу на более ликвидный инструмент-аналог.'),
('PORTFOLIO_CONTRIBUTION',6,'DIVERSIFY_MARKET_EXPOSURE','["target_market"]','Проверить вклад на другом ликвидном рынке.')
ON CONFLICT(gate_code) DO NOTHING;

CREATE TABLE IF NOT EXISTS analytics.edge_methodology_research_lineage_v1 (
    lineage_id uuid PRIMARY KEY,
    evaluation_id uuid NOT NULL REFERENCES analytics.edge_methodology_evaluation_v1(evaluation_id),
    parent_run_id uuid NOT NULL REFERENCES analytics.edge_search_scenario_run_v1(run_id),
    parent_result_id uuid NOT NULL REFERENCES analytics.walkforward_edge_search_v3(result_id),
    plan_id uuid NOT NULL REFERENCES analytics.edge_next_research_plan_v1(plan_id),
    plan_item_id uuid NOT NULL REFERENCES analytics.edge_next_research_plan_item_v1(plan_item_id),
    adaptive_scenario_id uuid NOT NULL REFERENCES analytics.edge_search_adaptive_scenario_v1(adaptive_scenario_id),
    gate_code text NOT NULL REFERENCES analytics.edge_methodology_remediation_rule_v1(gate_code),
    adaptation_code text NOT NULL,
    source_symbol text NOT NULL,
    target_symbol text NOT NULL,
    pass_gate_snapshot jsonb NOT NULL,
    holdout_policy jsonb NOT NULL,
    status_code text NOT NULL,
    created_at timestamptz NOT NULL DEFAULT clock_timestamp(),
    updated_at timestamptz NOT NULL DEFAULT clock_timestamp(),
    UNIQUE(evaluation_id,gate_code)
);

CREATE OR REPLACE FUNCTION analytics.guard_methodology_research_lineage_v1()
RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN
 IF TG_OP='UPDATE' AND (
   OLD.evaluation_id IS DISTINCT FROM NEW.evaluation_id OR
   OLD.gate_code IS DISTINCT FROM NEW.gate_code OR
   OLD.adaptation_code IS DISTINCT FROM NEW.adaptation_code OR
   OLD.source_symbol IS DISTINCT FROM NEW.source_symbol OR
   OLD.target_symbol IS DISTINCT FROM NEW.target_symbol OR
   OLD.pass_gate_snapshot IS DISTINCT FROM NEW.pass_gate_snapshot OR
   OLD.holdout_policy IS DISTINCT FROM NEW.holdout_policy) THEN
   RAISE EXCEPTION 'METHODOLOGY_RESEARCH_LINEAGE_IMMUTABLE';
 END IF;
 RETURN NEW;
END $$;

DROP TRIGGER IF EXISTS methodology_research_lineage_guard_v1 ON analytics.edge_methodology_research_lineage_v1;
CREATE TRIGGER methodology_research_lineage_guard_v1 BEFORE UPDATE
ON analytics.edge_methodology_research_lineage_v1 FOR EACH ROW
EXECUTE FUNCTION analytics.guard_methodology_research_lineage_v1();

CREATE OR REPLACE VIEW analytics.edge_methodology_research_queue_v1 AS
SELECT l.lineage_id,l.evaluation_id,l.gate_code,r.priority,l.adaptation_code,
       l.source_symbol,l.target_symbol,l.status_code,l.created_at,l.updated_at
FROM analytics.edge_methodology_research_lineage_v1 l
JOIN analytics.edge_methodology_remediation_rule_v1 r USING(gate_code)
ORDER BY CASE l.status_code WHEN 'ACTIVE' THEN 1 WHEN 'WAITING_FUTURE_DATA' THEN 2 ELSE 3 END,
         r.priority,l.created_at;

COMMIT;
