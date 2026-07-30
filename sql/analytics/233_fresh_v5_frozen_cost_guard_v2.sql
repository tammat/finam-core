BEGIN;

CREATE OR REPLACE VIEW analytics.fresh_v5_frozen_cost_admission_guard_v2 AS
WITH policy AS (
    SELECT * FROM analytics.fresh_v5_cost_admission_policy_v1
    WHERE policy_code='STRICT_OOS_V5' AND enabled
), grouped AS (
    SELECT c.portfolio_scope,c.symbol,
      coalesce(nullif(c.strategy,''),'UNASSIGNED') strategy_code,
      upper(coalesce(nullif(c.side,''),'UNKNOWN')) side_code,
      coalesce(nullif(c.payload->'context'->>'entry_session_msk',''),'UNKNOWN') session_code,
      coalesce(nullif(c.payload->'context'->>'entry_regime',''),nullif(c.entry_regime,''),'UNKNOWN') regime_code,
      coalesce(nullif(c.payload->'context'->>'actual_exit_reason',''),nullif(c.payload->'context'->>'exit_rule',''),'UNKNOWN') exit_code,
      count(*)::integer trades,round(sum(c.gross_pnl)::numeric,6) gross_pnl,
      round(sum(c.commission)::numeric,6) execution_cost,round(sum(c.net_pnl)::numeric,6) net_pnl,
      round(avg(c.net_pnl)::numeric,6) net_expectancy,round(avg(abs(c.gross_pnl))::numeric,6) average_gross_move,
      round(avg(c.commission)::numeric,6) average_execution_cost,
      round((coalesce(sum(c.net_pnl) FILTER(WHERE c.net_pnl>0),0)/
        nullif(abs(sum(c.net_pnl) FILTER(WHERE c.net_pnl<0)),0))::numeric,6) net_profit_factor,
      max(c.exit_ts) last_trade_at
    FROM analytics.closed_trades_fresh_v5_training_v1 c GROUP BY 1,2,3,4,5,6,7
)
SELECT g.*,p.minimum_trades,p.minimum_profit_factor,p.minimum_net_expectancy,p.cost_buffer_multiplier,
 CASE WHEN g.trades<p.minimum_trades THEN 'WAITING_SAMPLE'
      WHEN g.average_gross_move<=g.average_execution_cost*p.cost_buffer_multiplier THEN 'REJECTED_COSTS'
      WHEN g.net_expectancy<=p.minimum_net_expectancy THEN 'REJECTED_EXPECTANCY'
      WHEN g.net_profit_factor IS NULL THEN 'REJECTED_PROFIT_FACTOR_UNDEFINED'
      WHEN g.net_profit_factor<p.minimum_profit_factor THEN 'REJECTED_PROFIT_FACTOR' ELSE 'ELIGIBLE_OOS' END admission_status,
 CASE WHEN g.trades<p.minimum_trades THEN 'FRESH_V5_SAMPLE_BELOW_80'
      WHEN g.average_gross_move<=g.average_execution_cost*p.cost_buffer_multiplier THEN 'EXPECTED_MOVE_DOES_NOT_COVER_EXECUTION_COST_BUFFER'
      WHEN g.net_expectancy<=p.minimum_net_expectancy THEN 'NET_EXPECTANCY_NOT_POSITIVE'
      WHEN g.net_profit_factor IS NULL THEN 'NET_PROFIT_FACTOR_UNDEFINED'
      WHEN g.net_profit_factor<p.minimum_profit_factor THEN 'NET_PROFIT_FACTOR_BELOW_THRESHOLD'
      ELSE 'V5_FROZEN_COST_AND_EXPECTANCY_CONFIRMED' END reason_code
FROM grouped g CROSS JOIN policy p;

COMMENT ON VIEW analytics.fresh_v5_frozen_cost_admission_guard_v2 IS
'V5 cost admission только по замороженной training-когорте; OOS-наблюдения исключены.';
GRANT SELECT ON analytics.fresh_v5_frozen_cost_admission_guard_v2 TO alex,finam;

COMMIT;
