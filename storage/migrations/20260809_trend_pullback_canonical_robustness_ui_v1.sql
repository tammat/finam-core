BEGIN;

CREATE SCHEMA IF NOT EXISTS analytics;
CREATE SCHEMA IF NOT EXISTS marketcore_ui;

CREATE TABLE IF NOT EXISTS analytics.trend_pullback_canonical_robustness_v1 (
    id                      bigserial PRIMARY KEY,
    run_uuid                uuid NOT NULL,
    created_at              timestamptz NOT NULL DEFAULT now(),

    symbol                  text NOT NULL,
    strategy_code           text NOT NULL DEFAULT 'TREND_PULLBACK_V1',
    timeframe               text NOT NULL DEFAULT 'M5',

    variants_total          integer NOT NULL,
    positive_variants       integer NOT NULL,
    positive_neighbor_ratio numeric(12,6) NOT NULL,

    fold_stable_variants    integer NOT NULL,
    fold_count              integer NOT NULL DEFAULT 3,
    fold_stable_ratio       numeric(12,6) NOT NULL,

    robustness_status       text NOT NULL,
    robust                  boolean NOT NULL,

    execution_costs_used    boolean NOT NULL DEFAULT false,
    economic_edge_claimed   boolean NOT NULL DEFAULT false,

    runtime_changed         boolean NOT NULL DEFAULT false,
    execution_changed       boolean NOT NULL DEFAULT false,
    orders_changed          boolean NOT NULL DEFAULT false,
    fills_changed           boolean NOT NULL DEFAULT false,
    micro_live_allowed      boolean NOT NULL DEFAULT false,

    source_version          text NOT NULL
                            DEFAULT 'TREND_PULLBACK_CANONICAL_ROBUSTNESS_V1',

    CONSTRAINT trend_pullback_robustness_status_ck
        CHECK (robustness_status IN ('ROBUST', 'FRAGILE', 'FAIL'))
);

CREATE INDEX IF NOT EXISTS
    idx_trend_pullback_canonical_robustness_v1_run
ON analytics.trend_pullback_canonical_robustness_v1
    (run_uuid, symbol);

CREATE INDEX IF NOT EXISTS
    idx_trend_pullback_canonical_robustness_v1_created
ON analytics.trend_pullback_canonical_robustness_v1
    (created_at DESC);

CREATE OR REPLACE VIEW
marketcore_ui.trend_pullback_canonical_robustness_v1 AS
SELECT
    id,
    run_uuid,
    created_at,

    symbol,
    strategy_code,
    timeframe,

    variants_total,
    positive_variants,
    positive_neighbor_ratio,

    fold_stable_variants AS positive_fold_count,
    fold_count,
    fold_stable_ratio,

    robustness_status,
    robust,

    execution_costs_used,
    economic_edge_claimed,

    CASE
        WHEN robust = false
            THEN 'REJECT'
        WHEN execution_costs_used = false
            THEN 'WAIT_COST_VALIDATION'
        WHEN economic_edge_claimed = false
            THEN 'WAIT_ECONOMIC_EDGE'
        ELSE 'VALIDATED'
    END AS validation_status,

    runtime_changed,
    execution_changed,
    orders_changed,
    fills_changed,
    micro_live_allowed,

    source_version
FROM analytics.trend_pullback_canonical_robustness_v1;

COMMIT;
