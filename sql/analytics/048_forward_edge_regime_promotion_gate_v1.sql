CREATE TABLE IF NOT EXISTS analytics.forward_edge_regime_promotion_gate_v1 (
    cohort_id UUID NOT NULL,
    incubator_candidate_id UUID NOT NULL,
    policy_code TEXT NOT NULL,
    strategy_family TEXT NOT NULL,
    closed_observations INTEGER NOT NULL,
    calendar_days INTEGER NOT NULL,
    attributed_closed INTEGER NOT NULL,
    attribution_coverage NUMERIC NOT NULL,
    tested_regimes INTEGER NOT NULL,
    positive_regimes INTEGER NOT NULL,
    positive_regime_share NUMERIC NOT NULL,
    variant_net_pnl NUMERIC NOT NULL,
    baseline_net_pnl NUMERIC NOT NULL,
    net_pnl_delta NUMERIC NOT NULL,
    decision_code TEXT NOT NULL CHECK (decision_code IN ('READY_FOR_PAPER_REVIEW','HOLD_RESEARCH')),
    reason_codes JSONB NOT NULL,
    review_eligible BOOLEAN NOT NULL DEFAULT false,
    promotion_allowed BOOLEAN NOT NULL DEFAULT false,
    live_allowed BOOLEAN NOT NULL DEFAULT false,
    policy_version TEXT NOT NULL,
    source_version TEXT NOT NULL,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    PRIMARY KEY (cohort_id, incubator_candidate_id, policy_code)
);

CREATE INDEX IF NOT EXISTS idx_forward_edge_regime_promotion_gate_v1_decision
ON analytics.forward_edge_regime_promotion_gate_v1
(cohort_id, decision_code, review_eligible);
