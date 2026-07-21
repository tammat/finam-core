BEGIN;

ALTER TABLE analytics.walkforward_variant_task_v4
  ADD COLUMN IF NOT EXISTS pre_holdout_evidence jsonb NOT NULL DEFAULT '{}'::jsonb;

UPDATE analytics.edge_methodology_contract_v1
SET active=false
WHERE active;

INSERT INTO analytics.edge_methodology_contract_v1(
  contract_code,policy,policy_hash,active
) SELECT
  'METHODOLOGY_V3_COMPLETE_EVIDENCE',
  policy,
  md5(policy::text),
  true
FROM (SELECT jsonb_build_object(
    'gate_sequence',jsonb_build_array(
      'STATISTICAL_SIGNIFICANCE','PARAMETER_ROBUSTNESS','INDEPENDENT_HOLDOUT',
      'REALISTIC_EXECUTION','CAPACITY','PORTFOLIO_CONTRIBUTION'
    ),
    'max_fdr_q',0.10,
    'min_robust_neighbors',2,
    'neighbor_min_profit_factor',1.0,
    'neighbor_min_folds',3,
    'stress_cost_multiplier',1.5,
    'stress_min_profit_factor',1.0,
    'min_microstructure_coverage',0.80,
    'min_depth_coverage',0.80,
    'min_exchange_timestamp_coverage',0.80,
    'min_independent_trade_days',5,
    'min_independent_sessions',2,
    'min_independent_regimes',2,
    'min_capacity_rub',500000,
    'min_portfolio_overlap_days',5,
    'max_portfolio_abs_correlation',0.70,
    'future_only_remediation_required',true,
    'fold_overlap_forbidden',true,
    'all_gates_required',true
  ) AS policy) source
ON CONFLICT(contract_code) DO UPDATE SET active=true;

COMMIT;
