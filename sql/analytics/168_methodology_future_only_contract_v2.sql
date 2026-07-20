BEGIN;

-- Новый контракт создаётся отдельной версией: исторический контракт неизменяем.
UPDATE analytics.edge_methodology_contract_v1
SET active=false
WHERE active AND contract_code<>'METHODOLOGY_V2_FUTURE_ONLY';

INSERT INTO analytics.edge_methodology_contract_v1(
  contract_code,policy,policy_hash,active
) VALUES (
  'METHODOLOGY_V2_FUTURE_ONLY',
  '{"sequence":["STATISTICAL_SIGNIFICANCE","PARAMETER_ROBUSTNESS","INDEPENDENT_HOLDOUT","REALISTIC_EXECUTION","CAPACITY","PORTFOLIO_CONTRIBUTION"],"max_fdr_q":0.10,"min_robust_neighbors":2,"neighbor_min_profit_factor":1.0,"neighbor_min_folds":3,"stress_cost_multiplier":1.5,"stress_min_profit_factor":1.0,"min_microstructure_coverage":0.80,"min_independent_trade_days":5,"min_capacity_rub":500000,"max_portfolio_abs_correlation":0.75,"min_portfolio_overlap_days":20,"empty_portfolio_policy":"BASE_PORTFOLIO_ALLOWED","future_only_required_for_remediation":true,"fold_overlap_forbidden":true,"all_gates_required":true}'::jsonb,
  md5('{"sequence":["STATISTICAL_SIGNIFICANCE","PARAMETER_ROBUSTNESS","INDEPENDENT_HOLDOUT","REALISTIC_EXECUTION","CAPACITY","PORTFOLIO_CONTRIBUTION"],"max_fdr_q":0.10,"min_robust_neighbors":2,"neighbor_min_profit_factor":1.0,"neighbor_min_folds":3,"stress_cost_multiplier":1.5,"stress_min_profit_factor":1.0,"min_microstructure_coverage":0.80,"min_independent_trade_days":5,"min_capacity_rub":500000,"max_portfolio_abs_correlation":0.75,"min_portfolio_overlap_days":20,"empty_portfolio_policy":"BASE_PORTFOLIO_ALLOWED","future_only_required_for_remediation":true,"fold_overlap_forbidden":true,"all_gates_required":true}'::jsonb::text),
  true
)
ON CONFLICT(contract_code) DO UPDATE SET active=true;

COMMIT;
