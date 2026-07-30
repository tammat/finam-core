BEGIN;

CREATE TABLE IF NOT EXISTS analytics.v5_lifecycle_repair_audit_v1 (
    audited_at timestamptz NOT NULL,
    reason_code text NOT NULL,
    id bigint,
    portfolio_scope text,
    symbol text,
    strategy text,
    entry_price numeric,
    initial_qty numeric,
    remaining_qty numeric,
    current_stop numeric,
    current_take_profit numeric,
    raw jsonb,
    created_at timestamptz,
    updated_at timestamptz
);

INSERT INTO analytics.v5_lifecycle_repair_audit_v1
SELECT clock_timestamp(),'REBUILT_FROM_POSITION_PROJECTION_V1',l.id,l.portfolio_scope,l.symbol,
       l.strategy,l.entry_price,l.initial_qty,l.remaining_qty,l.current_stop,
       l.current_take_profit,l.raw,l.created_at,l.updated_at
FROM analytics.paper_research_position_lifecycle_v1 l
WHERE l.portfolio_scope LIKE 'FRESH_V5%';

CREATE TEMP TABLE v5_lifecycle_rebuild_v1 ON COMMIT DROP AS
WITH projection AS (
    SELECT p.portfolio_scope,p.symbol,
           COALESCE(NULLIF(p.state->>'net_qty','')::numeric,
                    NULLIF(p.state->>'qty','')::numeric,0) AS net_qty,
           COALESCE(NULLIF(p.state->>'avg_price','')::numeric,0) AS avg_price
    FROM analytics.paper_research_position_projection_v1 p
    WHERE p.portfolio_scope LIKE 'FRESH_V5%'
      AND p.symbol NOT LIKE 'TEST@%'
), latest AS (
    SELECT DISTINCT ON (l.portfolio_scope,l.symbol) l.*
    FROM analytics.paper_research_position_lifecycle_v1 l
    WHERE l.portfolio_scope LIKE 'FRESH_V5%'
    ORDER BY l.portfolio_scope,l.symbol,l.updated_at DESC NULLS LAST,l.created_at DESC,l.id DESC
)
SELECT p.portfolio_scope,p.symbol,COALESCE(l.strategy,'default') AS strategy,
       p.avg_price AS entry_price,abs(p.net_qty) AS initial_qty,
       abs(p.net_qty) AS remaining_qty,
       CASE WHEN abs(COALESCE(l.entry_price,0)-p.avg_price)<=greatest(0.000001,abs(p.avg_price)*0.000001)
            THEN COALESCE(l.tp1_done,false) ELSE false END AS tp1_done,
       CASE WHEN abs(COALESCE(l.entry_price,0)-p.avg_price)<=greatest(0.000001,abs(p.avg_price)*0.000001)
            THEN COALESCE(l.tp2_done,false) ELSE false END AS tp2_done,
       CASE WHEN abs(COALESCE(l.entry_price,0)-p.avg_price)<=greatest(0.000001,abs(p.avg_price)*0.000001)
            THEN COALESCE(l.profit_lock_done,false) ELSE false END AS profit_lock_done,
       CASE WHEN abs(COALESCE(l.entry_price,0)-p.avg_price)<=greatest(0.000001,abs(p.avg_price)*0.000001)
            THEN COALESCE(l.trailing_active,false) ELSE false END AS trailing_active,
       CASE WHEN abs(COALESCE(l.entry_price,0)-p.avg_price)<=greatest(0.000001,abs(p.avg_price)*0.000001)
            THEN l.current_stop END AS current_stop,
       CASE WHEN abs(COALESCE(l.entry_price,0)-p.avg_price)<=greatest(0.000001,abs(p.avg_price)*0.000001)
            THEN l.current_take_profit END AS current_take_profit,
       COALESCE(l.raw,'{}'::jsonb)||jsonb_build_object(
           'source','v5_lifecycle_projection_repair_v1',
           'projection_net_qty',p.net_qty,
           'previous_entry_price',l.entry_price
       ) AS raw,
       COALESCE(l.created_at,clock_timestamp()) AS created_at,
       clock_timestamp() AS updated_at
FROM projection p
LEFT JOIN latest l USING(portfolio_scope,symbol)
WHERE abs(p.net_qty)>0.000000001 AND p.avg_price>0;

DELETE FROM analytics.paper_research_position_lifecycle_v1
WHERE portfolio_scope LIKE 'FRESH_V5%';

ALTER TABLE analytics.paper_research_position_lifecycle_v1
DROP CONSTRAINT IF EXISTS paper_research_position_lifec_portfolio_scope_symbol_strate_key;
ALTER TABLE analytics.paper_research_position_lifecycle_v1
DROP CONSTRAINT IF EXISTS paper_research_position_lifecycle_scope_symbol_key;

INSERT INTO analytics.paper_research_position_lifecycle_v1(
    portfolio_scope,symbol,strategy,entry_price,initial_qty,remaining_qty,
    tp1_done,tp2_done,profit_lock_done,trailing_active,current_stop,
    current_take_profit,raw,created_at,updated_at
)
SELECT portfolio_scope,symbol,strategy,entry_price,initial_qty,remaining_qty,
       tp1_done,tp2_done,profit_lock_done,trailing_active,current_stop,
       current_take_profit,raw,created_at,updated_at
FROM v5_lifecycle_rebuild_v1;

ALTER TABLE analytics.paper_research_position_lifecycle_v1
ADD CONSTRAINT paper_research_position_lifecycle_scope_symbol_key
UNIQUE (portfolio_scope,symbol);

CREATE TABLE IF NOT EXISTS analytics.v5_signal_timeframe_repair_audit_v2 (
    audited_at timestamptz NOT NULL,
    signal_id text PRIMARY KEY,
    symbol text NOT NULL,
    old_timeframe text,
    new_timeframe text NOT NULL
);

INSERT INTO analytics.v5_signal_timeframe_repair_audit_v2
SELECT clock_timestamp(),s.signal_id,s.symbol,s.timeframe,
       CASE WHEN s.symbol LIKE 'NG%@RTSX' THEN 'M1' ELSE 'M5' END
FROM signals s
WHERE upper(COALESCE(s.timeframe,'')) IN ('','LIVE')
  AND EXISTS (
      SELECT 1 FROM analytics.closed_trades_fresh_v5_confirmed c
      WHERE c.signal_id=s.signal_id
  )
ON CONFLICT(signal_id) DO NOTHING;

UPDATE signals s SET timeframe=a.new_timeframe
FROM analytics.v5_signal_timeframe_repair_audit_v2 a
WHERE s.signal_id=a.signal_id
  AND upper(COALESCE(s.timeframe,'')) IN ('','LIVE');

UPDATE analytics.closed_trades_fresh_v5_confirmed c SET timeframe=a.new_timeframe
FROM analytics.v5_signal_timeframe_repair_audit_v2 a
WHERE c.signal_id=a.signal_id
  AND upper(COALESCE(c.timeframe,'')) IN ('','LIVE');

GRANT SELECT ON analytics.v5_lifecycle_repair_audit_v1 TO alex,finam;
GRANT SELECT ON analytics.v5_signal_timeframe_repair_audit_v2 TO alex,finam;

COMMIT;
