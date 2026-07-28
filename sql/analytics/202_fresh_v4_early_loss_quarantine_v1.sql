BEGIN;

CREATE TABLE IF NOT EXISTS analytics.fresh_v4_early_loss_policy_v1 (
    policy_code text PRIMARY KEY,
    enabled boolean NOT NULL DEFAULT true,
    early_review_trades integer NOT NULL CHECK (early_review_trades > 0),
    early_max_profit_factor numeric NOT NULL
        CHECK (early_max_profit_factor >= 0 AND early_max_profit_factor < 1),
    cost_buffer_multiplier numeric NOT NULL CHECK (cost_buffer_multiplier >= 1),
    updated_at timestamptz NOT NULL DEFAULT clock_timestamp()
);

INSERT INTO analytics.fresh_v4_early_loss_policy_v1(
    policy_code,early_review_trades,early_max_profit_factor,cost_buffer_multiplier
) VALUES ('STRICT_EARLY_V1',20,0.80,1.50)
ON CONFLICT(policy_code) DO UPDATE SET
    enabled=true,
    early_review_trades=excluded.early_review_trades,
    early_max_profit_factor=excluded.early_max_profit_factor,
    cost_buffer_multiplier=excluded.cost_buffer_multiplier,
    updated_at=clock_timestamp();

CREATE OR REPLACE VIEW analytics.fresh_v4_early_loss_quarantine_v1 AS
SELECT
    g.*,
    p.early_review_trades,
    p.early_max_profit_factor,
    p.cost_buffer_multiplier AS early_cost_buffer_multiplier,
    CASE
        WHEN g.trades >= p.early_review_trades
         AND g.net_expectancy < 0
         AND (
             g.net_profit_factor < p.early_max_profit_factor
             OR g.average_gross_move <= g.average_execution_cost * p.cost_buffer_multiplier
         ) THEN true
        ELSE false
    END AS quarantined,
    CASE
        WHEN g.trades >= p.early_review_trades
         AND g.net_expectancy < 0
         AND (
             g.net_profit_factor < p.early_max_profit_factor
             OR g.average_gross_move <= g.average_execution_cost * p.cost_buffer_multiplier
         ) THEN 'EARLY_NEGATIVE_AFTER_COSTS'
        ELSE 'CONTINUE_OBSERVATION'
    END AS quarantine_reason_code
FROM analytics.fresh_v4_cost_admission_guard_v1 g
CROSS JOIN analytics.fresh_v4_early_loss_policy_v1 p
WHERE p.policy_code='STRICT_EARLY_V1' AND p.enabled;

COMMENT ON VIEW analytics.fresh_v4_early_loss_quarantine_v1 IS
'Ранний карантин точных V4-связок после 20 явно убыточных сделок. Исходные сделки сохраняются; порог OOS 80 и критерии PASS не меняются.';

GRANT SELECT ON analytics.fresh_v4_early_loss_policy_v1 TO alex,finam;
GRANT SELECT ON analytics.fresh_v4_early_loss_quarantine_v1 TO alex,finam;

COMMIT;
