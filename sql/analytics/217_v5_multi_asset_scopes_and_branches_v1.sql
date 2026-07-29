BEGIN;

INSERT INTO analytics.paper_portfolio_scope_v1(
    scope_code,asset_group,enabled,starts_at,source_version
) VALUES
 ('FRESH_V5_USD_PERPETUAL','FUTURES',true,clock_timestamp(),'V5_MULTI_ASSET_BRANCH_V1'),
 ('FRESH_V5_GOLD_FUTURES','FUTURES',true,clock_timestamp(),'V5_MULTI_ASSET_BRANCH_V1'),
 ('FRESH_V5_CNY_PERPETUAL','FUTURES',true,clock_timestamp(),'V5_MULTI_ASSET_BRANCH_V1')
ON CONFLICT(scope_code) DO UPDATE SET enabled=true,source_version=excluded.source_version,
updated_at=clock_timestamp();

CREATE TABLE IF NOT EXISTS analytics.v5_asset_scope_map_v1(
    asset_code text PRIMARY KEY CHECK(asset_code IN ('USD','GOLD','CNY')),
    symbol text UNIQUE NOT NULL,
    scope_code text UNIQUE NOT NULL REFERENCES analytics.paper_portfolio_scope_v1(scope_code),
    enabled boolean NOT NULL DEFAULT true,
    updated_at timestamptz NOT NULL DEFAULT clock_timestamp()
);

INSERT INTO analytics.v5_asset_scope_map_v1(asset_code,symbol,scope_code) VALUES
 ('USD','USDRUBF@RTSX','FRESH_V5_USD_PERPETUAL'),
 ('GOLD','GDU6@RTSX','FRESH_V5_GOLD_FUTURES'),
 ('CNY','CNYRUBF@RTSX','FRESH_V5_CNY_PERPETUAL')
ON CONFLICT(asset_code) DO UPDATE SET symbol=excluded.symbol,scope_code=excluded.scope_code,
enabled=true,updated_at=clock_timestamp();

CREATE TABLE IF NOT EXISTS analytics.v5_asset_branch_policy_v1(
    asset_code text NOT NULL CHECK(asset_code IN ('USD','GOLD','CNY')),
    symbol text NOT NULL,
    timeframe_code text NOT NULL CHECK(timeframe_code IN ('M1','M5')),
    side_code text NOT NULL CHECK(side_code IN ('LONG','SHORT')),
    strategy_code text NOT NULL,
    scope_code text NOT NULL REFERENCES analytics.paper_portfolio_scope_v1(scope_code),
    execution_stage text NOT NULL DEFAULT 'PAPER' CHECK(execution_stage IN ('SHADOW','PAPER')),
    cost_guard_required boolean NOT NULL DEFAULT true,
    session_guard_required boolean NOT NULL DEFAULT true,
    direction_guard_required boolean NOT NULL DEFAULT true,
    candle_exit_required boolean NOT NULL DEFAULT true,
    trailing_dry_run_required boolean NOT NULL DEFAULT true,
    funding_cost_required boolean NOT NULL DEFAULT false,
    enabled boolean NOT NULL DEFAULT true,
    updated_at timestamptz NOT NULL DEFAULT clock_timestamp(),
    PRIMARY KEY(asset_code,timeframe_code,side_code)
);

INSERT INTO analytics.v5_asset_branch_policy_v1(
 asset_code,symbol,timeframe_code,side_code,strategy_code,scope_code
)
SELECT asset,symbol,timeframe,side,strategy,scope
FROM (VALUES
 ('USD','USDRUBF@RTSX','USD_REGIME_FUTURES','FRESH_V5_USD_PERPETUAL'),
 ('GOLD','GDU6@RTSX','GOLD_TREND_BREAKOUT','FRESH_V5_GOLD_FUTURES'),
 ('CNY','CNYRUBF@RTSX','CNY_REGIME_FUTURES','FRESH_V5_CNY_PERPETUAL')
) a(asset,symbol,strategy,scope)
CROSS JOIN (VALUES('M1'),('M5')) t(timeframe)
CROSS JOIN (VALUES('LONG'),('SHORT')) s(side)
ON CONFLICT(asset_code,timeframe_code,side_code) DO UPDATE SET
 symbol=excluded.symbol,strategy_code=excluded.strategy_code,scope_code=excluded.scope_code,
 cost_guard_required=true,session_guard_required=true,direction_guard_required=true,
 candle_exit_required=true,trailing_dry_run_required=true,
 funding_cost_required=(excluded.asset_code IN ('USD','CNY')),
 enabled=true,updated_at=clock_timestamp();

UPDATE analytics.v5_asset_branch_policy_v1
SET funding_cost_required=(asset_code IN ('USD','CNY')),updated_at=clock_timestamp();

-- The active-universe governance trigger requires a physical strategy policy
-- for every selectable timeframe. Clone the already governed M5 definitions;
-- this expands only the research clock and does not relax strategy controls.
INSERT INTO analytics.runtime_strategy_policy_v2(
 symbol,timeframe,regime_family,strategy_code,generator_code,enabled,
 priority,assignment_reason,updated_at
)
SELECT symbol,'M1',regime_family,strategy_code,generator_code,enabled,
       priority,assignment_reason||'; V5 M1 isolated branch',clock_timestamp()
FROM analytics.runtime_strategy_policy_v2
WHERE timeframe='M5' AND enabled
  AND symbol IN ('USDRUBF@RTSX','CNYRUBF@RTSX','GDU6@RTSX')
ON CONFLICT(symbol,timeframe,regime_family) DO UPDATE SET
 strategy_code=excluded.strategy_code,generator_code=excluded.generator_code,
 enabled=excluded.enabled,priority=excluded.priority,
 assignment_reason=excluded.assignment_reason,updated_at=excluded.updated_at;

CREATE OR REPLACE FUNCTION analytics.resolve_paper_portfolio_scope_v1(
    p_symbol text,
    p_execution_type text DEFAULT 'paper'
) RETURNS text
LANGUAGE sql STABLE AS $$
    WITH explicit_scope AS (
      SELECT m.scope_code,1 AS rank
      FROM analytics.v5_asset_scope_map_v1 m
      JOIN analytics.paper_portfolio_scope_v1 s ON s.scope_code=m.scope_code AND s.enabled
      WHERE m.enabled AND m.symbol=p_symbol
        AND lower(coalesce(p_execution_type,'')) LIKE 'paper%'
    ), fallback_scope AS (
      SELECT s.scope_code,2 AS rank
      FROM analytics.paper_portfolio_scope_v1 s
      WHERE s.enabled AND now()>=s.starts_at
        AND s.scope_code NOT IN (SELECT scope_code FROM analytics.v5_asset_scope_map_v1 WHERE enabled)
        AND lower(coalesce(p_execution_type,'')) LIKE 'paper%'
        AND s.asset_group=CASE WHEN upper(coalesce(p_symbol,'')) LIKE '%@MISX' THEN 'EQUITY'
                               WHEN upper(coalesce(p_symbol,'')) LIKE '%@RTSX' THEN 'FUTURES' END
      ORDER BY s.starts_at DESC LIMIT 1
    )
    SELECT scope_code FROM (
      SELECT * FROM explicit_scope UNION ALL SELECT * FROM fallback_scope
    ) q ORDER BY rank LIMIT 1
$$;

INSERT INTO analytics.paper_scope_runtime_policy_v1(scope_code,enabled,allow_scope_bootstrap,reason)
SELECT scope_code,true,true,'Isolated V5 asset scope; all cost/session/direction gates remain mandatory'
FROM analytics.v5_asset_scope_map_v1
ON CONFLICT(scope_code) DO UPDATE SET enabled=true,allow_scope_bootstrap=true,
reason=excluded.reason,updated_at=now();

CREATE OR REPLACE VIEW analytics.closed_trades_fresh_v5_confirmed AS
SELECT * FROM public.closed_trades
WHERE portfolio_scope IN (
 'FRESH_V5_CONFIRMED_EQUITY','FRESH_V5_CONFIRMED_FUTURES',
 'FRESH_V5_USD_PERPETUAL','FRESH_V5_GOLD_FUTURES','FRESH_V5_CNY_PERPETUAL'
)
AND payload->'context'->>'cohort'=portfolio_scope
AND payload->'context'->>'regime_source_version'='CANDLE_REGIME_V3'
AND COALESCE((payload->'context'->>'regime_confirmed_bars')::integer,0)>=3
AND payload->'context'->>'regime_trend' IN ('trend_up','trend_down','range')
AND payload->'context'->>'regime_vol' IN ('low_vol','normal_vol','high_vol')
AND (payload->'context'->>'regime_trend'='range'
 OR (payload->'context'->>'regime_trend'='trend_up' AND upper(payload->'context'->>'side')='BUY')
 OR (payload->'context'->>'regime_trend'='trend_down' AND upper(payload->'context'->>'side')='SELL'));

GRANT SELECT ON analytics.v5_asset_scope_map_v1,analytics.v5_asset_branch_policy_v1 TO alex,finam;
GRANT SELECT,INSERT,UPDATE,DELETE ON analytics.v5_asset_scope_map_v1,analytics.v5_asset_branch_policy_v1 TO alex;

COMMIT;
