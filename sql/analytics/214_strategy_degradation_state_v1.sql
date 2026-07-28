BEGIN;

CREATE SCHEMA IF NOT EXISTS analytics;

CREATE TABLE IF NOT EXISTS analytics.strategy_degradation_state_v1 (
    strategy_family text PRIMARY KEY,
    sample_size integer NOT NULL DEFAULT 0,
    expectancy_rub numeric,
    profit_factor numeric,
    status text NOT NULL DEFAULT 'UNASSESSED'
        CHECK (status IN ('UNASSESSED', 'NORMAL', 'ELEVATED', 'BLOCKED')),
    scale_factor numeric NOT NULL DEFAULT 1.0
        CHECK (scale_factor >= 0 AND scale_factor <= 1),
    reason text NOT NULL DEFAULT 'insufficient_sample',
    calculated_at timestamptz NOT NULL DEFAULT now()
);

COMMENT ON TABLE analytics.strategy_degradation_state_v1 IS
    'Latest audited strategy degradation state consumed by the portfolio risk gate.';

GRANT SELECT, INSERT, UPDATE, DELETE
    ON analytics.strategy_degradation_state_v1 TO alex, finam;

COMMIT;
