BEGIN;

CREATE TABLE IF NOT EXISTS analytics.fresh_v5_cost_admission_policy_v1 (
    policy_code text PRIMARY KEY,
    enabled boolean NOT NULL DEFAULT true,
    minimum_trades integer NOT NULL CHECK (minimum_trades > 0),
    minimum_profit_factor numeric NOT NULL CHECK (minimum_profit_factor >= 1),
    minimum_net_expectancy numeric NOT NULL DEFAULT 0,
    cost_buffer_multiplier numeric NOT NULL CHECK (cost_buffer_multiplier >= 1),
    updated_at timestamptz NOT NULL DEFAULT clock_timestamp()
);

INSERT INTO analytics.fresh_v5_cost_admission_policy_v1(
    policy_code, minimum_trades, minimum_profit_factor,
    minimum_net_expectancy, cost_buffer_multiplier
) VALUES ('STRICT_OOS_V5', 80, 1.15, 0, 1.50)
ON CONFLICT(policy_code) DO UPDATE SET
    enabled = true,
    minimum_trades = excluded.minimum_trades,
    minimum_profit_factor = excluded.minimum_profit_factor,
    minimum_net_expectancy = excluded.minimum_net_expectancy,
    cost_buffer_multiplier = excluded.cost_buffer_multiplier,
    updated_at = clock_timestamp();

CREATE OR REPLACE VIEW analytics.fresh_v5_cost_admission_guard_v1 AS
WITH policy AS (
    SELECT *
    FROM analytics.fresh_v5_cost_admission_policy_v1
    WHERE policy_code = 'STRICT_OOS_V5' AND enabled
), grouped AS (
    SELECT
        c.portfolio_scope,
        c.symbol,
        coalesce(nullif(c.strategy, ''), 'UNASSIGNED') AS strategy_code,
        upper(coalesce(nullif(c.side, ''), 'UNKNOWN')) AS side_code,
        coalesce(nullif(c.payload->'context'->>'entry_session_msk', ''), 'UNKNOWN') AS session_code,
        coalesce(
            nullif(c.payload->'context'->>'entry_regime', ''),
            nullif(c.entry_regime, ''),
            concat_ws('_',
                nullif(c.payload->'context'->>'regime_trend', ''),
                nullif(c.payload->'context'->>'regime_vol', '')
            ),
            'UNKNOWN'
        ) AS regime_code,
        coalesce(
            nullif(c.payload->'context'->>'actual_exit_reason', ''),
            nullif(c.payload->'context'->>'exit_rule', ''),
            'UNKNOWN'
        ) AS exit_code,
        count(*)::integer AS trades,
        round(sum(c.gross_pnl)::numeric, 6) AS gross_pnl,
        round(sum(c.commission)::numeric, 6) AS execution_cost,
        round(sum(c.net_pnl)::numeric, 6) AS net_pnl,
        round(avg(c.net_pnl)::numeric, 6) AS net_expectancy,
        round(avg(abs(c.gross_pnl))::numeric, 6) AS average_gross_move,
        round(avg(c.commission)::numeric, 6) AS average_execution_cost,
        round((
            coalesce(sum(c.net_pnl) FILTER (WHERE c.net_pnl > 0), 0)
            / nullif(abs(sum(c.net_pnl) FILTER (WHERE c.net_pnl < 0)), 0)
        )::numeric, 6) AS net_profit_factor,
        max(c.exit_ts) AS last_trade_at
    FROM analytics.closed_trades_fresh_v5_confirmed c
    GROUP BY 1,2,3,4,5,6,7
)
SELECT
    g.*,
    p.minimum_trades,
    p.minimum_profit_factor,
    p.minimum_net_expectancy,
    p.cost_buffer_multiplier,
    CASE
        WHEN g.trades < p.minimum_trades THEN 'WAITING_SAMPLE'
        WHEN g.average_gross_move <= g.average_execution_cost * p.cost_buffer_multiplier
            THEN 'REJECTED_COSTS'
        WHEN g.net_expectancy <= p.minimum_net_expectancy THEN 'REJECTED_EXPECTANCY'
        WHEN g.net_profit_factor IS NULL THEN 'REJECTED_PROFIT_FACTOR_UNDEFINED'
        WHEN g.net_profit_factor < p.minimum_profit_factor THEN 'REJECTED_PROFIT_FACTOR'
        ELSE 'ELIGIBLE_OOS'
    END AS admission_status,
    CASE
        WHEN g.trades < p.minimum_trades THEN 'FRESH_V5_SAMPLE_BELOW_80'
        WHEN g.average_gross_move <= g.average_execution_cost * p.cost_buffer_multiplier
            THEN 'EXPECTED_MOVE_DOES_NOT_COVER_EXECUTION_COST_BUFFER'
        WHEN g.net_expectancy <= p.minimum_net_expectancy THEN 'NET_EXPECTANCY_NOT_POSITIVE'
        WHEN g.net_profit_factor IS NULL THEN 'NET_PROFIT_FACTOR_UNDEFINED'
        WHEN g.net_profit_factor < p.minimum_profit_factor THEN 'NET_PROFIT_FACTOR_BELOW_THRESHOLD'
        ELSE 'V5_COST_AND_EXPECTANCY_CONFIRMED'
    END AS reason_code
FROM grouped g
CROSS JOIN policy p;

CREATE TABLE IF NOT EXISTS analytics.fresh_v5_early_loss_policy_v1 (
    policy_code text PRIMARY KEY,
    enabled boolean NOT NULL DEFAULT true,
    early_review_trades integer NOT NULL CHECK (early_review_trades > 0),
    early_max_profit_factor numeric NOT NULL
        CHECK (early_max_profit_factor >= 0 AND early_max_profit_factor < 1),
    cost_buffer_multiplier numeric NOT NULL CHECK (cost_buffer_multiplier >= 1),
    updated_at timestamptz NOT NULL DEFAULT clock_timestamp()
);

INSERT INTO analytics.fresh_v5_early_loss_policy_v1(
    policy_code, early_review_trades, early_max_profit_factor, cost_buffer_multiplier
) VALUES ('STRICT_EARLY_V5', 20, 0.80, 1.50)
ON CONFLICT(policy_code) DO UPDATE SET
    enabled = true,
    early_review_trades = excluded.early_review_trades,
    early_max_profit_factor = excluded.early_max_profit_factor,
    cost_buffer_multiplier = excluded.cost_buffer_multiplier,
    updated_at = clock_timestamp();

CREATE OR REPLACE VIEW analytics.fresh_v5_early_loss_quarantine_v1 AS
SELECT
    g.*,
    p.early_review_trades,
    p.early_max_profit_factor,
    p.cost_buffer_multiplier AS early_cost_buffer_multiplier,
    CASE
        WHEN g.trades >= p.early_review_trades
         AND g.net_expectancy < 0
         AND (
             coalesce(g.net_profit_factor, 0) < p.early_max_profit_factor
             OR g.average_gross_move <= g.average_execution_cost * p.cost_buffer_multiplier
         ) THEN true
        ELSE false
    END AS quarantined,
    CASE
        WHEN g.trades >= p.early_review_trades
         AND g.net_expectancy < 0
         AND (
             coalesce(g.net_profit_factor, 0) < p.early_max_profit_factor
             OR g.average_gross_move <= g.average_execution_cost * p.cost_buffer_multiplier
         ) THEN 'EARLY_V5_NEGATIVE_AFTER_COSTS'
        ELSE 'CONTINUE_V5_OBSERVATION'
    END AS quarantine_reason_code
FROM analytics.fresh_v5_cost_admission_guard_v1 g
CROSS JOIN analytics.fresh_v5_early_loss_policy_v1 p
WHERE p.policy_code = 'STRICT_EARLY_V5' AND p.enabled;

COMMENT ON VIEW analytics.fresh_v5_cost_admission_guard_v1 IS
'Строгий допуск чистой V5-когорты: 80 сделок, реальные издержки, положительное ожидание и PF не ниже 1.15.';
COMMENT ON VIEW analytics.fresh_v5_early_loss_quarantine_v1 IS
'Ранний карантин убыточных V5-связок после 20 сделок; исходные данные не удаляются.';

GRANT SELECT ON analytics.fresh_v5_cost_admission_policy_v1 TO alex,finam;
GRANT SELECT ON analytics.fresh_v5_cost_admission_guard_v1 TO alex,finam;
GRANT SELECT ON analytics.fresh_v5_early_loss_policy_v1 TO alex,finam;
GRANT SELECT ON analytics.fresh_v5_early_loss_quarantine_v1 TO alex,finam;

COMMIT;
