CREATE TABLE IF NOT EXISTS analytics.forward_edge_loss_decomposition_v1 (
    cohort_id UUID NOT NULL,
    incubator_candidate_id UUID NOT NULL,
    policy_code TEXT NOT NULL,
    strategy_family TEXT NOT NULL,
    regime_code TEXT NOT NULL,
    closed_observations INTEGER NOT NULL,
    entry_reference_observations INTEGER NOT NULL,
    entry_reference_coverage NUMERIC NOT NULL,
    reference_gross_pnl NUMERIC NOT NULL,
    entry_timing_cost NUMERIC NOT NULL,
    realized_baseline_gross_pnl NUMERIC NOT NULL,
    commission_cost NUMERIC NOT NULL,
    spread_cost NUMERIC NOT NULL,
    slippage_cost NUMERIC NOT NULL,
    baseline_net_pnl NUMERIC NOT NULL,
    exit_policy_effect NUMERIC NOT NULL,
    variant_net_pnl NUMERIC NOT NULL,
    reconciliation_error NUMERIC NOT NULL,
    dominant_loss_driver TEXT NOT NULL,
    data_quality_status TEXT NOT NULL,
    source_version TEXT NOT NULL,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    PRIMARY KEY (cohort_id, incubator_candidate_id, policy_code, regime_code)
);

CREATE INDEX IF NOT EXISTS idx_forward_edge_loss_decomposition_v1_driver
ON analytics.forward_edge_loss_decomposition_v1
(cohort_id, dominant_loss_driver, variant_net_pnl);

ALTER TABLE analytics.forward_edge_loss_decomposition_v1
DROP CONSTRAINT IF EXISTS forward_edge_loss_decomposition_v1_data_quality_status_check;
ALTER TABLE analytics.forward_edge_loss_decomposition_v1
ADD CONSTRAINT forward_edge_loss_decomposition_v1_data_quality_status_check
CHECK (data_quality_status IN ('COMPLETE','PARTIAL_ENTRY_REFERENCE','PARTIAL_COST_MODEL','RECONCILIATION_ERROR'));
