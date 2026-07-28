BEGIN;

CREATE TABLE IF NOT EXISTS analytics.paper_portfolio_scope_v1 (
    scope_code text PRIMARY KEY,
    asset_group text NOT NULL CHECK (asset_group IN ('EQUITY','FUTURES')),
    enabled boolean NOT NULL DEFAULT false,
    starts_at timestamptz NOT NULL,
    source_version text NOT NULL,
    updated_at timestamptz NOT NULL DEFAULT clock_timestamp()
);

INSERT INTO analytics.paper_portfolio_scope_v1(scope_code,asset_group,enabled,starts_at,source_version)
VALUES
 ('FRESH_V3_EQUITY','EQUITY',true,clock_timestamp(),'FRESH_V3_PHYSICAL_ISOLATION_V1'),
 ('FRESH_V3_FUTURES','FUTURES',true,clock_timestamp(),'FRESH_V3_PHYSICAL_ISOLATION_V1')
ON CONFLICT(scope_code) DO UPDATE SET
 enabled=excluded.enabled, source_version=excluded.source_version, updated_at=clock_timestamp();

CREATE OR REPLACE FUNCTION analytics.resolve_paper_portfolio_scope_v1(
    p_symbol text,
    p_execution_type text DEFAULT 'paper'
) RETURNS text
LANGUAGE sql STABLE AS $$
    SELECT s.scope_code
    FROM analytics.paper_portfolio_scope_v1 s
    WHERE s.enabled
      AND lower(coalesce(p_execution_type,'')) LIKE 'paper%'
      AND s.asset_group = CASE
          WHEN upper(coalesce(p_symbol,'')) LIKE '%@MISX' THEN 'EQUITY'
          WHEN upper(coalesce(p_symbol,'')) LIKE '%@RTSX' THEN 'FUTURES'
          ELSE NULL
      END
      AND now() >= s.starts_at
    ORDER BY s.starts_at DESC
    LIMIT 1
$$;

ALTER TABLE public.fills ADD COLUMN IF NOT EXISTS portfolio_scope text;
ALTER TABLE public.signal_fills ADD COLUMN IF NOT EXISTS portfolio_scope text;
ALTER TABLE public.trades ADD COLUMN IF NOT EXISTS portfolio_scope text;
ALTER TABLE public.closed_trades ADD COLUMN IF NOT EXISTS portfolio_scope text;
CREATE INDEX IF NOT EXISTS fills_scope_symbol_ts_idx ON public.fills(portfolio_scope,symbol,ts,fill_id);
CREATE INDEX IF NOT EXISTS closed_trades_scope_closed_idx ON public.closed_trades(portfolio_scope,closed_at DESC);

CREATE TABLE IF NOT EXISTS analytics.paper_research_position_projection_v1 (
    portfolio_scope text NOT NULL,
    symbol text NOT NULL,
    state jsonb NOT NULL,
    updated_at timestamptz NOT NULL DEFAULT now(),
    PRIMARY KEY(portfolio_scope,symbol)
);

CREATE TABLE IF NOT EXISTS analytics.paper_research_position_lifecycle_v1 (
    id bigserial PRIMARY KEY,
    portfolio_scope text NOT NULL,
    symbol text NOT NULL,
    strategy text NOT NULL DEFAULT 'default',
    entry_price numeric,
    initial_qty numeric,
    remaining_qty numeric,
    tp1_done boolean DEFAULT false,
    tp2_done boolean DEFAULT false,
    profit_lock_done boolean DEFAULT false,
    trailing_active boolean DEFAULT false,
    current_stop numeric,
    current_take_profit numeric,
    raw jsonb DEFAULT '{}'::jsonb,
    created_at timestamptz NOT NULL DEFAULT now(),
    updated_at timestamptz NOT NULL DEFAULT now(),
    UNIQUE(portfolio_scope,symbol,strategy)
);

CREATE OR REPLACE VIEW analytics.closed_trades_fresh_v3 AS
SELECT *
FROM public.closed_trades
WHERE portfolio_scope IN ('FRESH_V3_EQUITY','FRESH_V3_FUTURES')
  AND payload->'context'->>'cohort' = portfolio_scope;

COMMIT;
