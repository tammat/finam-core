BEGIN;

GRANT USAGE ON SCHEMA analytics TO alex;
GRANT SELECT ON analytics.runtime_strategy_assignment_v1 TO alex;
GRANT SELECT ON analytics.regime_strategy_routing_policy_v1 TO alex;
GRANT SELECT,INSERT,UPDATE ON analytics.paper_closed_trade_materializer_checkpoint_v2 TO alex;
GRANT SELECT,INSERT,UPDATE ON public.persistent_kill_switch TO alex;
GRANT USAGE,SELECT ON SEQUENCE public.persistent_kill_switch_id_seq TO alex;

CREATE TABLE IF NOT EXISTS analytics.legacy_projection_quarantine_audit_v1 AS
SELECT clock_timestamp() AS audited_at,p.portfolio_scope,p.symbol,p.state,p.updated_at,
       'EXCLUDED_FROM_V5_PORTFOLIO_RISK'::text AS reason
FROM analytics.paper_research_position_projection_v1 p
WHERE p.portfolio_scope NOT LIKE 'FRESH_V5%' OR p.symbol LIKE 'TEST@%'
WITH NO DATA;

INSERT INTO analytics.legacy_projection_quarantine_audit_v1
SELECT clock_timestamp(),p.portfolio_scope,p.symbol,p.state,p.updated_at,
       'EXCLUDED_FROM_V5_PORTFOLIO_RISK'
FROM analytics.paper_research_position_projection_v1 p
WHERE (p.portfolio_scope NOT LIKE 'FRESH_V5%' OR p.symbol LIKE 'TEST@%')
  AND abs(coalesce(nullif(p.state->>'qty','')::numeric,0))>0
  AND NOT EXISTS (
    SELECT 1 FROM analytics.legacy_projection_quarantine_audit_v1 a
    WHERE a.portfolio_scope=p.portfolio_scope AND a.symbol=p.symbol
      AND a.updated_at=p.updated_at
  );

CREATE TABLE IF NOT EXISTS analytics.v5_timeframe_repair_audit_v1 AS
SELECT clock_timestamp() audited_at,id trade_id,symbol,timeframe old_timeframe,
       CASE WHEN symbol LIKE 'NG%@RTSX' THEN 'M1' ELSE 'M5' END new_timeframe
FROM analytics.closed_trades_fresh_v5_confirmed WITH NO DATA;

INSERT INTO analytics.v5_timeframe_repair_audit_v1
SELECT clock_timestamp(),id,symbol,timeframe,
       CASE WHEN symbol LIKE 'NG%@RTSX' THEN 'M1' ELSE 'M5' END
FROM analytics.closed_trades_fresh_v5_confirmed c
WHERE upper(coalesce(timeframe,'')) IN ('','LIVE')
  AND NOT EXISTS(SELECT 1 FROM analytics.v5_timeframe_repair_audit_v1 a WHERE a.trade_id=c.id);

UPDATE analytics.closed_trades_fresh_v5_confirmed c SET timeframe=a.new_timeframe
FROM analytics.v5_timeframe_repair_audit_v1 a
WHERE c.id=a.trade_id AND upper(coalesce(c.timeframe,'')) IN ('','LIVE');

GRANT SELECT ON analytics.legacy_projection_quarantine_audit_v1 TO alex,finam;
GRANT SELECT ON analytics.v5_timeframe_repair_audit_v1 TO alex,finam;

COMMIT;
