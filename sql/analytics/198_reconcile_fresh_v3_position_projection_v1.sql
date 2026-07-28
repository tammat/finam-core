BEGIN;

-- Восстанавливаем чистую V3-проекцию только из fills того же портфеля.
-- Legacy/реальный портфель в расчёт не попадает.
WITH net AS (
    SELECT portfolio_scope,symbol,
           sum(CASE WHEN upper(side)='BUY' THEN qty ELSE -qty END)::numeric AS net_qty,
           count(*) AS fills_count,
           max(ts) AS last_fill_ts
    FROM public.fills
    WHERE portfolio_scope IN ('FRESH_V3_EQUITY','FRESH_V3_FUTURES')
    GROUP BY portfolio_scope,symbol
), life AS (
    SELECT DISTINCT ON (portfolio_scope,symbol)
           portfolio_scope,symbol,entry_price
    FROM analytics.paper_research_position_lifecycle_v1
    ORDER BY portfolio_scope,symbol,updated_at DESC
)
INSERT INTO analytics.paper_research_position_projection_v1(portfolio_scope,symbol,state,updated_at)
SELECT n.portfolio_scope,n.symbol,
       jsonb_build_object(
           'symbol',n.symbol,
           'qty',n.net_qty,
           'net_qty',n.net_qty,
           'avg_price',l.entry_price,
           'fills_count_projected',n.fills_count,
           'last_fill_ts',n.last_fill_ts,
           'source','RECONCILE_FRESH_V3_POSITION_PROJECTION_V1'
       ),clock_timestamp()
FROM net n
LEFT JOIN life l USING(portfolio_scope,symbol)
ON CONFLICT(portfolio_scope,symbol) DO UPDATE
SET state=excluded.state,updated_at=excluded.updated_at;

COMMIT;
