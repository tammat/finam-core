CREATE TABLE IF NOT EXISTS analytics.forward_edge_regime_attribution_v1 (
    cohort_id UUID NOT NULL,
    policy_code TEXT NOT NULL,
    regime_code TEXT NOT NULL,
    observations_total INTEGER NOT NULL,
    baseline_closed INTEGER NOT NULL,
    baseline_net_pnl NUMERIC NOT NULL,
    baseline_win_rate NUMERIC,
    variant_closed INTEGER NOT NULL,
    variant_net_pnl NUMERIC NOT NULL,
    variant_win_rate NUMERIC,
    net_pnl_delta NUMERIC NOT NULL,
    avg_regime_confidence NUMERIC,
    max_snapshot_age_seconds NUMERIC,
    attribution_status TEXT NOT NULL CHECK (attribution_status IN ('ATTRIBUTED', 'UNKNOWN')),
    source_version TEXT NOT NULL,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    PRIMARY KEY (cohort_id, policy_code, regime_code)
);

CREATE INDEX IF NOT EXISTS idx_forward_edge_regime_attribution_v1_rank
ON analytics.forward_edge_regime_attribution_v1
(cohort_id, policy_code, net_pnl_delta DESC);
