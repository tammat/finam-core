BEGIN;

DROP INDEX IF EXISTS analytics.v5_oos_included_trade_once_idx;

ALTER TABLE analytics.v5_oos_observation_audit_v1
  ADD COLUMN IF NOT EXISTS event_cluster_id text;
ALTER TABLE analytics.v5_oos_run_v1
  ADD COLUMN IF NOT EXISTS raw_observations_included integer NOT NULL DEFAULT 0,
  ADD COLUMN IF NOT EXISTS effective_observations integer NOT NULL DEFAULT 0;
ALTER TABLE analytics.v5_oos_run_v1
  ALTER COLUMN source_version SET DEFAULT 'V5_PURGED_OOS_WORKER_V2';

CREATE OR REPLACE FUNCTION analytics.v5_oos_event_cluster_id_v2(
  p_symbol text,p_entry_ts timestamptz,p_exit_ts timestamptz) RETURNS text
LANGUAGE sql IMMUTABLE PARALLEL SAFE AS $$
 SELECT concat_ws('|',
   CASE
     WHEN upper(p_symbol) ~ '^(BR|NG)' THEN 'ENERGY'
     WHEN upper(p_symbol) ~ '^(CNY|USDRUB|EURRUB|SI)' THEN 'FX'
     WHEN upper(p_symbol) ~ '^(SBER|SBERP)' THEN 'SBER_GROUP'
     ELSE regexp_replace(upper(coalesce(p_symbol,'UNKNOWN')),'@.*$','')
   END,
   to_char(p_entry_ts AT TIME ZONE 'Europe/Moscow','YYYY-MM-DD'))
$$;

UPDATE analytics.v5_oos_reuse_policy_v1 SET enabled=false,
 reason='Отменено: одно будущее событие разрешено всем гипотезам, зарегистрированным до него; запрет reuse действует внутри run и между train/OOS',
 updated_at=clock_timestamp() WHERE policy_code='V5_OOS_GLOBAL_TRADE_ONCE';

INSERT INTO analytics.v5_oos_reuse_policy_v1(policy_code,uniqueness_scope,enabled,reason)
VALUES('V5_OOS_PREREGISTERED_SHARED_EVENT','GLOBAL_SOURCE_TRADE',true,
 'Одна будущая сделка может независимо оценивать все гипотезы, зарегистрированные до её входа; внутри run повтор запрещён UNIQUE(run_id,source_trade_id)')
ON CONFLICT(policy_code) DO UPDATE SET enabled=true,reason=excluded.reason,updated_at=clock_timestamp();

CREATE OR REPLACE VIEW analytics.closed_trades_fresh_v5_training_v1 AS
SELECT c.* FROM analytics.closed_trades_fresh_v5_confirmed c
WHERE NOT EXISTS (
 SELECT 1 FROM analytics.trade_outcome_oos_admission_v1 a
 WHERE a.status_code IN ('QUEUED','RUNNING','OOS_PASS','OOS_FAIL')
 AND c.exit_ts > (a.oos_request->'temporal_isolation'->>'purge_before_ts')::timestamptz
 AND c.symbol=a.oos_request->>'symbol'
 AND coalesce(nullif(c.strategy,''),'UNASSIGNED')=a.oos_request->>'paper_strategy_code'
 AND upper(coalesce(nullif(c.side,''),'UNKNOWN'))=upper(a.oos_request->>'side_code')
 AND (a.oos_request->>'session_code' IS NULL OR coalesce(nullif(c.payload->'context'->>'entry_session_msk',''),'UNKNOWN')=a.oos_request->>'session_code')
 AND (a.oos_request->>'regime_code' IS NULL OR coalesce(nullif(c.payload->'context'->>'entry_regime',''),nullif(c.entry_regime,''),'UNKNOWN')=a.oos_request->>'regime_code')
 AND (a.oos_request->>'holding_code' IS NULL OR coalesce(nullif(c.payload->'context'->>'planned_exit_rule',''),nullif(c.payload->'context'->>'exit_rule',''),'UNKNOWN')=a.oos_request->>'holding_code')
);

DROP VIEW analytics.fresh_v5_frozen_cost_admission_guard_v2;
CREATE VIEW analytics.fresh_v5_frozen_cost_admission_guard_v2 AS
WITH policy AS (SELECT * FROM analytics.fresh_v5_cost_admission_policy_v1 WHERE policy_code='STRICT_OOS_V5' AND enabled),
grouped AS (
 SELECT c.portfolio_scope,c.symbol,coalesce(nullif(c.strategy,''),'UNASSIGNED') strategy_code,
 upper(coalesce(nullif(c.side,''),'UNKNOWN')) side_code,
 coalesce(nullif(c.payload->'context'->>'entry_session_msk',''),'UNKNOWN') session_code,
 coalesce(nullif(c.payload->'context'->>'entry_regime',''),nullif(c.entry_regime,''),'UNKNOWN') regime_code,
 coalesce(nullif(c.payload->'context'->>'planned_exit_rule',''),nullif(c.payload->'context'->>'exit_rule',''),'UNKNOWN') exit_code,
 count(*)::integer trades,round(sum(c.gross_pnl)::numeric,6) gross_pnl,
 round(sum(greatest(coalesce(c.commission,0),abs(coalesce(c.gross_pnl,0)-coalesce(c.net_pnl,0)))+
   2*spec.one_tick_cost*abs(c.qty))::numeric,6) execution_cost,
 round(sum(c.net_pnl)::numeric,6) net_pnl,round(avg(c.net_pnl)::numeric,6) net_expectancy,
 round(avg(abs(c.gross_pnl))::numeric,6) average_gross_move,
 round(avg(greatest(coalesce(c.commission,0),abs(coalesce(c.gross_pnl,0)-coalesce(c.net_pnl,0)))+
   2*spec.one_tick_cost*abs(c.qty))::numeric,6) average_execution_cost,
 bool_and(spec.one_tick_cost>0) cost_model_complete,
 round((coalesce(sum(c.net_pnl) FILTER(WHERE c.net_pnl>0),0)/nullif(abs(sum(c.net_pnl) FILTER(WHERE c.net_pnl<0)),0))::numeric,6) net_profit_factor,
 max(c.exit_ts) last_trade_at
 FROM analytics.closed_trades_fresh_v5_training_v1 c
 LEFT JOIN LATERAL (
   SELECT CASE WHEN upper(c.symbol) LIKE '%@RTSX' THEN coalesce(s.tick_value,0)
               ELSE coalesce(s.tick_size,0)*coalesce(s.lot_size,0) END one_tick_cost
   FROM analytics.market_contract_spec_v1 s
   WHERE s.is_active AND (s.symbol=c.symbol OR s.symbol=c.root_symbol OR
     s.symbol=regexp_replace(c.symbol,'@.*$',''))
   ORDER BY (s.symbol=c.symbol) DESC,s.valid_from DESC LIMIT 1
 ) spec ON true GROUP BY 1,2,3,4,5,6,7
)
SELECT g.*,p.minimum_trades,p.minimum_profit_factor,p.minimum_net_expectancy,p.cost_buffer_multiplier,
 CASE WHEN NOT g.cost_model_complete THEN 'WAITING_MICROSTRUCTURE'
 WHEN g.trades<p.minimum_trades THEN 'WAITING_SAMPLE'
 WHEN g.average_gross_move<=g.average_execution_cost*p.cost_buffer_multiplier THEN 'REJECTED_COSTS'
 WHEN g.net_expectancy<=p.minimum_net_expectancy THEN 'REJECTED_EXPECTANCY'
 WHEN g.net_profit_factor IS NULL OR g.net_profit_factor<p.minimum_profit_factor THEN 'REJECTED_PROFIT_FACTOR' ELSE 'ELIGIBLE_OOS' END admission_status,
 CASE WHEN NOT g.cost_model_complete THEN 'CONSERVATIVE_SPREAD_SLIPPAGE_FLOOR_UNAVAILABLE'
 WHEN g.trades<p.minimum_trades THEN 'FRESH_V5_SAMPLE_BELOW_80'
 WHEN g.average_gross_move<=g.average_execution_cost*p.cost_buffer_multiplier THEN 'EXPECTED_MOVE_DOES_NOT_COVER_EXECUTION_COST_BUFFER'
 WHEN g.net_expectancy<=p.minimum_net_expectancy THEN 'NET_EXPECTANCY_NOT_POSITIVE'
 WHEN g.net_profit_factor IS NULL OR g.net_profit_factor<p.minimum_profit_factor THEN 'NET_PROFIT_FACTOR_BELOW_THRESHOLD'
 ELSE 'V5_FROZEN_FULL_COST_AND_EXPECTANCY_CONFIRMED' END reason_code
FROM grouped g CROSS JOIN policy p;

COMMENT ON VIEW analytics.fresh_v5_frozen_cost_admission_guard_v2 IS
'V5 admission: только entry-time контекст; полный cost telemetry обязателен; OOS исключён из training.';
GRANT SELECT ON analytics.fresh_v5_frozen_cost_admission_guard_v2 TO alex,finam;
COMMIT;
