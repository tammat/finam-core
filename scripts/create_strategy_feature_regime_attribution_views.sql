create or replace view analytics_strategy_regime_attribution_v2 as
select
    analytics_symbol,
    strategy,

    coalesce(regime, 'UNKNOWN') as regime,
    coalesce(source, 'UNKNOWN') as source,

    case
        when (payload->>'confidence')::numeric >= 0.80 then 'HIGH_CONFIDENCE'
        when (payload->>'confidence')::numeric >= 0.50 then 'MEDIUM_CONFIDENCE'
        else 'LOW_CONFIDENCE'
    end as confidence_bucket,

    count(*) as fills,

    round(sum(signed_cashflow)::numeric, 6) as signed_cashflow,
    round(avg(signed_cashflow)::numeric, 6) as avg_signed_cashflow,
    round(avg((payload->>'confidence')::numeric)::numeric, 4) as avg_confidence,

    min(ts_msk) as first_ts_msk,
    max(ts_msk) as last_ts_msk

from analytics_trades_normalized
where strategy is not null
  and strategy <> ''
group by
    analytics_symbol,
    strategy,
    coalesce(regime, 'UNKNOWN'),
    coalesce(source, 'UNKNOWN'),
    confidence_bucket;
