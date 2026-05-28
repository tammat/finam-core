-- BR_FILTERED_V2 validation report
-- Purpose:
--   Validate Brent filtered V2 policy on historical rolling Brent replay.
--
-- Dataset:
--   symbol: BR_ROLLING@RTSX
--   strategy: HISTORICAL_BREAKOUT_V1
--   run_id: br_rolling_breakout_v1_20250528_20260528
--
-- Interpretation:
--   V2_ALLOWED = trades allowed by BR_FILTERED_V2 profile rules.
--   V2_BLOCKED = trades blocked by BR_FILTERED_V2 profile rules.
--   weighted_pnl = trade_pnl * size_multiplier.
--
-- Expected baseline observed during validation:
--   V2_ALLOWED: trades=965, raw_pnl=68.9800, weighted_pnl=55.4110, avg_multiplier=0.7759
--   V2_BLOCKED: trades=2713, raw_pnl=-110.5600, weighted_pnl=0.0000

\echo 'BR_FILTERED_V2_VALIDATION_REPORT'

with enriched as (
  select
    p.trade_pnl,
    upper(t.side) as side,
    coalesce(r.regime, 'unknown') as regime,
    coalesce(r.volatility_regime, 'unknown') as volatility_regime,
    coalesce(r.session_type, 'unknown') as session_type,
    coalesce(r.confidence, 0.0) as confidence
  from analytics_intraday_pnl p
  join trades t
    on t.id = p.trade_id
  left join lateral (
    select r.*
    from analytics_regime_snapshots_v2 r
    where r.symbol = t.symbol
      and r.timeframe = t.timeframe
      and r.ts <= t.ts
    order by r.ts desc
    limit 1
  ) r on true
  where t.symbol = 'BR_ROLLING@RTSX'
    and t.strategy = 'HISTORICAL_BREAKOUT_V1'
    and t.payload->>'run_id' = 'br_rolling_breakout_v1_20250528_20260528'
    and t.is_invalid = false
),
scored as (
  select
    *,
    case
      when side='SELL'
       and confidence >= 0.65
       and regime='trend_up_expansion'
       and volatility_regime='high'
       and session_type='main_2'
        then 1.00

      when side='SELL'
       and confidence >= 0.65
       and regime='trend_up_expansion'
       and volatility_regime='high'
       and session_type='evening'
        then 0.85

      when side='SELL'
       and confidence >= 0.65
       and regime='trend_up_expansion'
       and volatility_regime='high'
       and session_type='main_1'
        then 0.80

      when side='SELL'
       and confidence >= 0.65
       and regime='range_normal'
       and volatility_regime='normal'
       and session_type='morning'
        then 0.75

      when side='SELL'
       and confidence >= 0.65
       and regime='trend_up'
       and volatility_regime='normal'
       and session_type='main_1'
        then 0.75

      when side='SELL'
       and confidence >= 0.65
       and regime='trend_up'
       and volatility_regime='normal'
       and session_type='evening'
        then 0.65

      else 0.0
    end as multiplier
  from enriched
)
select
  case when multiplier > 0 then 'V2_ALLOWED' else 'V2_BLOCKED' end as bucket,
  count(*) as trades,
  round(sum(trade_pnl)::numeric, 4) as raw_pnl,
  round(sum(trade_pnl * multiplier)::numeric, 4) as weighted_pnl,
  round(avg(trade_pnl * nullif(multiplier, 0))::numeric, 6) as weighted_expectancy_allowed_only,
  round(avg(multiplier)::numeric, 4) as avg_multiplier
from scored
group by 1
order by 1;

\echo 'BR_FILTERED_V2_ALLOWED_PROFILE_BREAKDOWN'

with enriched as (
  select
    p.trade_pnl,
    upper(t.side) as side,
    coalesce(r.regime, 'unknown') as regime,
    coalesce(r.volatility_regime, 'unknown') as volatility_regime,
    coalesce(r.session_type, 'unknown') as session_type,
    coalesce(r.confidence, 0.0) as confidence
  from analytics_intraday_pnl p
  join trades t
    on t.id = p.trade_id
  left join lateral (
    select r.*
    from analytics_regime_snapshots_v2 r
    where r.symbol = t.symbol
      and r.timeframe = t.timeframe
      and r.ts <= t.ts
    order by r.ts desc
    limit 1
  ) r on true
  where t.symbol = 'BR_ROLLING@RTSX'
    and t.strategy = 'HISTORICAL_BREAKOUT_V1'
    and t.payload->>'run_id' = 'br_rolling_breakout_v1_20250528_20260528'
    and t.is_invalid = false
),
scored as (
  select
    *,
    case
      when side='SELL' and confidence >= 0.65 and regime='trend_up_expansion' and volatility_regime='high' and session_type='main_2' then 1.00
      when side='SELL' and confidence >= 0.65 and regime='trend_up_expansion' and volatility_regime='high' and session_type='evening' then 0.85
      when side='SELL' and confidence >= 0.65 and regime='trend_up_expansion' and volatility_regime='high' and session_type='main_1' then 0.80
      when side='SELL' and confidence >= 0.65 and regime='range_normal' and volatility_regime='normal' and session_type='morning' then 0.75
      when side='SELL' and confidence >= 0.65 and regime='trend_up' and volatility_regime='normal' and session_type='main_1' then 0.75
      when side='SELL' and confidence >= 0.65 and regime='trend_up' and volatility_regime='normal' and session_type='evening' then 0.65
      else 0.0
    end as multiplier
  from enriched
)
select
  regime,
  volatility_regime,
  session_type,
  multiplier,
  count(*) as trades,
  round(sum(trade_pnl)::numeric, 4) as raw_pnl,
  round(sum(trade_pnl * multiplier)::numeric, 4) as weighted_pnl,
  round(avg(trade_pnl)::numeric, 6) as raw_expectancy
from scored
where multiplier > 0
group by 1,2,3,4
order by weighted_pnl desc;
