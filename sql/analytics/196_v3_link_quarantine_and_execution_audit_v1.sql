BEGIN;

CREATE TABLE IF NOT EXISTS analytics.v3_link_quarantine_v1(
    quarantine_key text PRIMARY KEY,
    portfolio_scope text NOT NULL,
    symbol text NOT NULL,
    strategy_code text NOT NULL,
    side_code text NOT NULL DEFAULT '*',
    reason_code text NOT NULL,
    evidence jsonb NOT NULL DEFAULT '{}'::jsonb,
    enabled boolean NOT NULL DEFAULT true,
    release_condition jsonb NOT NULL,
    created_at timestamptz NOT NULL DEFAULT clock_timestamp(),
    updated_at timestamptz NOT NULL DEFAULT clock_timestamp()
);

INSERT INTO analytics.v3_link_quarantine_v1(
    quarantine_key,portfolio_scope,symbol,strategy_code,side_code,reason_code,evidence,release_condition
) VALUES (
    'FRESH_V3_EQUITY|X5@MISX|VOLATILITY_BREAKOUT_EQUITY|*',
    'FRESH_V3_EQUITY','X5@MISX','VOLATILITY_BREAKOUT_EQUITY','*',
    'NEGATIVE_EXPECTANCY_COMMISSION_DOMINATED',
    jsonb_build_object(
        'detected_from','analytics.closed_trades_active_v3',
        'observed_trades',20,
        'observed_wins',0,
        'observed_net_pnl',-33.20,
        'audit_required',jsonb_build_array('PRICE_SCALE','COMMISSION','STOP_PRICE','TAKE_PRICE','SIDE')
    ),
    jsonb_build_object(
        'minimum_trades_per_side',30,
        'expectancy_after_costs','> 0',
        'profit_factor','>= 1.10',
        'stop_take_levels_required',true,
        'manual_allow_forbidden',true
    )
) ON CONFLICT(quarantine_key) DO UPDATE SET
    reason_code=excluded.reason_code,evidence=excluded.evidence,
    release_condition=excluded.release_condition,enabled=true,updated_at=clock_timestamp();

ALTER TABLE analytics.archive_v3_oos_bridge_v1
    DROP CONSTRAINT IF EXISTS archive_v3_oos_bridge_v1_readiness_code_check;
ALTER TABLE analytics.archive_v3_oos_bridge_v1
    ADD CONSTRAINT archive_v3_oos_bridge_v1_readiness_code_check CHECK(readiness_code IN(
        'WAITING_SAMPLE','WAITING_CONTEXT','FAILED_FRESH_EVIDENCE','QUARANTINED','READY_FOR_OOS','QUEUED'
    ));

CREATE OR REPLACE VIEW analytics.v3_execution_normalization_audit_v1 AS
SELECT
    coalesce(c.payload->'context'->>'portfolio_scope',c.payload->'context'->>'cohort','') portfolio_scope,
    c.symbol,coalesce(nullif(c.strategy,''),'UNKNOWN') strategy_code,coalesce(nullif(c.side,''),'UNKNOWN') side_code,
    count(*)::integer trades,
    count(*) FILTER(WHERE c.net_pnl>0)::integer wins,
    round(avg(c.entry_price)::numeric,6) average_entry_price,
    round(avg(abs(c.exit_price-c.entry_price))::numeric,6) average_absolute_move,
    round(avg(c.commission)::numeric,6) average_commission,
    round(sum(c.gross_pnl)::numeric,6) gross_pnl,
    round(sum(c.net_pnl)::numeric,6) net_pnl,
    round(avg(c.net_pnl)::numeric,6) expectancy_after_costs,
    count(*) FILTER(WHERE nullif(c.payload->'context'->>'stop_price','') IS NOT NULL)::integer stop_levels_recorded,
    count(*) FILTER(WHERE nullif(c.payload->'context'->>'take_price','') IS NOT NULL)::integer take_levels_recorded,
    CASE
      WHEN avg(c.entry_price)<=0 OR avg(c.exit_price)<=0 THEN 'PRICE_SCALE_INVALID'
      WHEN avg(abs(c.exit_price-c.entry_price))<=avg(c.commission) THEN 'COMMISSION_DOMINATES_MOVE'
      WHEN avg(c.net_pnl)<=0 THEN 'NEGATIVE_EXPECTANCY'
      ELSE 'NORMALIZED'
    END audit_status
FROM analytics.closed_trades_active_v3 c
WHERE coalesce(c.payload->'context'->>'portfolio_scope',c.payload->'context'->>'cohort','')
      IN ('FRESH_V3_EQUITY','FRESH_V3_FUTURES')
GROUP BY 1,2,3,4;

GRANT SELECT,INSERT,UPDATE ON analytics.v3_link_quarantine_v1 TO alex,finam;
GRANT SELECT ON analytics.v3_execution_normalization_audit_v1 TO alex,finam;

COMMIT;
