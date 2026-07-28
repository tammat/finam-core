BEGIN;

CREATE TABLE IF NOT EXISTS analytics.fresh_v4_cost_admission_policy_v1 (
    policy_code text PRIMARY KEY,
    enabled boolean NOT NULL DEFAULT true,
    minimum_trades integer NOT NULL CHECK (minimum_trades > 0),
    minimum_profit_factor numeric NOT NULL CHECK (minimum_profit_factor >= 1),
    minimum_net_expectancy numeric NOT NULL DEFAULT 0,
    cost_buffer_multiplier numeric NOT NULL CHECK (cost_buffer_multiplier >= 1),
    updated_at timestamptz NOT NULL DEFAULT clock_timestamp()
);

INSERT INTO analytics.fresh_v4_cost_admission_policy_v1(
    policy_code,minimum_trades,minimum_profit_factor,
    minimum_net_expectancy,cost_buffer_multiplier
) VALUES (
    'STRICT_OOS_V1',80,1.15,0,1.50
)
ON CONFLICT(policy_code) DO UPDATE SET
    enabled=true,
    minimum_trades=excluded.minimum_trades,
    minimum_profit_factor=excluded.minimum_profit_factor,
    minimum_net_expectancy=excluded.minimum_net_expectancy,
    cost_buffer_multiplier=excluded.cost_buffer_multiplier,
    updated_at=clock_timestamp();

CREATE OR REPLACE VIEW analytics.fresh_v4_cost_admission_guard_v1 AS
WITH policy AS (
    SELECT *
    FROM analytics.fresh_v4_cost_admission_policy_v1
    WHERE policy_code='STRICT_OOS_V1' AND enabled
), grouped AS (
    SELECT
        c.portfolio_scope,
        c.symbol,
        coalesce(nullif(c.strategy,''),'UNASSIGNED') AS strategy_code,
        upper(coalesce(nullif(c.side,''),'UNKNOWN')) AS side_code,
        coalesce(nullif(c.payload->'context'->>'entry_session_msk',''),'UNKNOWN') AS session_code,
        coalesce(nullif(c.payload->'context'->>'entry_regime',''),nullif(c.entry_regime,''),'UNKNOWN') AS regime_code,
        coalesce(
            nullif(c.payload->'context'->>'actual_exit_reason',''),
            nullif(c.payload->'context'->>'exit_rule',''),
            'UNKNOWN'
        ) AS exit_code,
        count(*)::integer AS trades,
        round(sum(c.gross_pnl)::numeric,6) AS gross_pnl,
        round(sum(c.commission)::numeric,6) AS execution_cost,
        round(sum(c.net_pnl)::numeric,6) AS net_pnl,
        round(avg(c.net_pnl)::numeric,6) AS net_expectancy,
        round(avg(abs(c.gross_pnl))::numeric,6) AS average_gross_move,
        round(avg(c.commission)::numeric,6) AS average_execution_cost,
        round(
            CASE
                WHEN abs(coalesce(sum(c.net_pnl) FILTER (WHERE c.net_pnl < 0),0))=0 THEN NULL
                ELSE coalesce(sum(c.net_pnl) FILTER (WHERE c.net_pnl > 0),0)
                     / abs(sum(c.net_pnl) FILTER (WHERE c.net_pnl < 0))
            END::numeric,6
        ) AS net_profit_factor,
        max(c.exit_ts) AS last_trade_at,
        abs(coalesce(sum(c.net_pnl) FILTER (WHERE c.net_pnl < 0),0)) > 0
            AS profit_factor_observable
    FROM analytics.closed_trades_fresh_v4_assigned c
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
        WHEN NOT g.profit_factor_observable THEN 'WAITING_PROFIT_FACTOR'
        WHEN g.average_gross_move <= g.average_execution_cost * p.cost_buffer_multiplier
            THEN 'REJECTED_COSTS'
        WHEN g.net_expectancy <= p.minimum_net_expectancy THEN 'REJECTED_EXPECTANCY'
        WHEN g.net_profit_factor < p.minimum_profit_factor THEN 'REJECTED_PROFIT_FACTOR'
        ELSE 'ELIGIBLE_OOS'
    END AS admission_status,
    CASE
        WHEN g.trades < p.minimum_trades THEN 'FRESH_SAMPLE_BELOW_80'
        WHEN NOT g.profit_factor_observable THEN 'PROFIT_FACTOR_NOT_OBSERVABLE'
        WHEN g.average_gross_move <= g.average_execution_cost * p.cost_buffer_multiplier
            THEN 'EXPECTED_MOVE_DOES_NOT_COVER_EXECUTION_COST_BUFFER'
        WHEN g.net_expectancy <= p.minimum_net_expectancy THEN 'NET_EXPECTANCY_NOT_POSITIVE'
        WHEN g.net_profit_factor < p.minimum_profit_factor THEN 'NET_PROFIT_FACTOR_BELOW_THRESHOLD'
        ELSE 'V4_COST_AND_EXPECTANCY_CONFIRMED'
    END AS reason_code
FROM grouped g
CROSS JOIN policy p;

ALTER TABLE analytics.trade_outcome_oos_admission_v1
    DROP CONSTRAINT IF EXISTS trade_outcome_oos_admission_v1_status_code_check;
ALTER TABLE analytics.trade_outcome_oos_admission_v1
    ADD CONSTRAINT trade_outcome_oos_admission_v1_status_code_check
    CHECK (status_code IN (
        'WAITING_HYPOTHESIS','WAITING_FRESH_DATA','WAITING_CONTEXT',
        'WAITING_MICROSTRUCTURE','REJECTED_COSTS','QUEUED','CLOSED'
    ));

ALTER TABLE analytics.trade_outcome_oos_admission_v1
    ADD COLUMN IF NOT EXISTS net_expectancy numeric,
    ADD COLUMN IF NOT EXISTS net_profit_factor numeric,
    ADD COLUMN IF NOT EXISTS execution_cost numeric,
    ADD COLUMN IF NOT EXISTS cost_admission_status text;

GRANT SELECT ON analytics.fresh_v4_cost_admission_policy_v1 TO alex,finam;
GRANT SELECT ON analytics.fresh_v4_cost_admission_guard_v1 TO alex,finam;

COMMIT;
