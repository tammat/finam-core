BEGIN;

CREATE TABLE IF NOT EXISTS analytics.trend_pullback_equity_base_cost_validation_v1 (
    id                  bigserial PRIMARY KEY,
    run_uuid            uuid NOT NULL,
    created_at          timestamptz NOT NULL DEFAULT now(),

    symbol              text NOT NULL,
    strategy_code       text NOT NULL DEFAULT 'TREND_PULLBACK_V1',
    timeframe           text NOT NULL DEFAULT 'M5',

    trades              integer NOT NULL,

    gross_pnl           numeric NOT NULL,
    gross_profit_factor numeric NOT NULL,
    gross_expectancy    numeric NOT NULL,

    commission          numeric NOT NULL,
    slippage            numeric NOT NULL,
    total_cost          numeric NOT NULL,

    net_pnl             numeric NOT NULL,
    net_expectancy      numeric NOT NULL,
    net_profit_factor   numeric NOT NULL,
    net_winrate         numeric NOT NULL,
    max_drawdown        numeric NOT NULL,
    cost_to_gross_ratio numeric NOT NULL,

    cost_validation_status text NOT NULL,
    economic_edge_claimed boolean NOT NULL DEFAULT false,
    micro_live_allowed    boolean NOT NULL DEFAULT false,

    source_version text NOT NULL
        DEFAULT 'TREND_PULLBACK_CANONICAL_EQUITY_BASE_COST_VALIDATION_V1',

    CONSTRAINT trend_pullback_equity_base_cost_status_ck
        CHECK (
            cost_validation_status IN (
                'SURVIVE_AFTER_BASE_COSTS',
                'REJECT_AFTER_BASE_COSTS'
            )
        ),

    UNIQUE (run_uuid, symbol)
);

CREATE OR REPLACE VIEW
marketcore_ui.trend_pullback_equity_base_cost_validation_v1 AS
SELECT
    id,
    run_uuid,
    created_at,
    symbol,
    strategy_code,
    timeframe,
    trades,

    gross_pnl,
    gross_profit_factor,
    gross_expectancy,

    commission,
    slippage,
    total_cost,

    net_pnl,
    net_expectancy,
    net_profit_factor,
    net_winrate,
    max_drawdown,
    cost_to_gross_ratio,

    cost_validation_status,

    CASE
        WHEN cost_validation_status='REJECT_AFTER_BASE_COSTS'
            THEN 'REJECT'
        WHEN economic_edge_claimed=false
            THEN 'WAIT_EXECUTION_VALIDATION'
        ELSE 'VALIDATED'
    END AS validation_status,

    economic_edge_claimed,
    micro_live_allowed,
    source_version
FROM analytics.trend_pullback_equity_base_cost_validation_v1;

COMMIT;
