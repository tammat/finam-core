create or replace view v_grafana_alerts_ru as
with latest_flow as (
    select distinct on (symbol)
        symbol,
        regime,
        bias,
        confidence,
        reason,
        ts
    from institutional_flow_regime_events
    order by symbol, ts desc
),

latest_liquidity as (
    select distinct on (continuous_symbol)
        continuous_symbol,
        preferred_symbol,
        score,
        ts
    from cross_contract_liquidity_decisions
    order by continuous_symbol, ts desc
)

select
    lf.ts as "🕒 Время",

    lf.symbol as "📈 Инструмент",

    case
        when lf.regime = 'ACCUMULATION'
            then '🟢 НАКОПЛЕНИЕ'
        when lf.regime = 'TREND_INITIATION'
            then '🚀 ЗАПУСК ТРЕНДА'
        when lf.regime = 'BREAKOUT_TRAP'
            then '🪤 ЛОВУШКА ПРОБОЯ'
        when lf.regime = 'DISTRIBUTION'
            then '🔴 РАСПРЕДЕЛЕНИЕ'
        when lf.regime = 'INSTITUTIONAL_PARTICIPATION'
            then '🏦 КРУПНЫЙ УЧАСТНИК'
        else '⚪ NORMAL_FLOW'
    end as "🚨 Alert",

    case
        when lf.bias = 'LONG_BIAS'
            then '🟢 LONG'
        when lf.bias = 'SHORT_BIAS'
            then '🔴 SHORT'
        when lf.bias = 'MOMENTUM_BIAS'
            then '🚀 MOMENTUM'
        when lf.bias = 'FADE_BIAS'
            then '🪤 FADE'
        else '⚪ NEUTRAL'
    end as "🧭 Bias",

    round(lf.confidence::numeric, 6) as "🎯 Уверенность",

    lf.reason as "📝 Причина"

from latest_flow lf

where
    lf.regime in (
        'ACCUMULATION',
        'TREND_INITIATION',
        'BREAKOUT_TRAP',
        'DISTRIBUTION',
        'INSTITUTIONAL_PARTICIPATION'
    )

union all

select
    ll.ts as "🕒 Время",

    ll.continuous_symbol as "📈 Инструмент",

    '🔄 СМЕНА ЛИКВИДНОГО КОНТРАКТА' as "🚨 Alert",

    '💧 LIQUIDITY_ROUTING' as "🧭 Bias",

    round(ll.score::numeric, 6) as "🎯 Уверенность",

    format(
        'continuous=%s preferred=%s score=%s',
        ll.continuous_symbol,
        ll.preferred_symbol,
        ll.score
    ) as "📝 Причина"

from latest_liquidity ll

where ll.score > 0

order by 1 desc;
