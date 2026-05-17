from __future__ import annotations

import os

import psycopg2


SQL = """
with latest as (
    select distinct on (symbol)
        id,
        symbol,
        asset_class,
        calculated_at,
        coalesce(atr_pct, 0.0) as atr_pct,
        coalesce(rvol, 0.0) as rvol,
        coalesce(smart_money_score, 0.0) as smart_money_score,
        coalesce(regime, '') as regime,
        extract(epoch from (now() - calculated_at)) / 60.0 as signal_age_min
    from market_opportunity_metrics
    order by symbol, calculated_at desc
),

calendar_risk as (
    select
        instrument_group,
        max(
            case
                when event_time >= now()
                 and event_time <= now() + interval '2 hours'
                then 1.0
                when event_time > now() + interval '2 hours'
                 and event_time <= now() + interval '24 hours'
                then 0.5
                else 0.0
            end
        ) as event_penalty
    from market_event_calendar
    where is_active = true
    group by instrument_group
),

churn as (
    select
        symbol,
        max(
            case
                when reason like '%Критический churn%' then 1.0
                when reason like '%Высокий churn%' then 0.5
                else 0.0
            end
        ) as churn_penalty
    from strategy_runtime_control
    group by symbol
),

scored as (
    select
        l.id,
        l.symbol,

        least(greatest(l.atr_pct / 0.03, 0.0), 1.0) as volatility_score,
        least(greatest(l.rvol / 3.0, 0.0), 1.0) as rvol_score,

        case
            when l.regime ilike '%trend_up_high_vol%' then 1.0
            when l.regime ilike '%trend_down_high_vol%' then 1.0
            when l.regime ilike '%trend_up%' then 0.75
            when l.regime ilike '%trend_down%' then 0.75
            when l.regime ilike '%flat%' then 0.25
            else 0.5
        end as trend_efficiency_score,

        case
            when l.asset_class in ('FUTURES', 'FUTURES_CONTINUOUS') then 0.8
            when l.asset_class = 'EQUITY' then 0.7
            else 0.5
        end as liquidity_score_v2,

        0.8 as spread_quality_score,

        coalesce(
            case
                when l.symbol like 'BR%' then br.event_penalty
                when l.symbol like 'NG%' then ng.event_penalty
                when l.symbol like 'USDRUB%' then fx.event_penalty
                else 0.0
            end,
            0.0
        ) as event_risk_penalty,

        coalesce(c.churn_penalty, 0.0) as churn_penalty,

        l.smart_money_score,
        l.signal_age_min,

        case
            when l.signal_age_min <= 15 then 1.0
            when l.signal_age_min <= 30 then 0.8
            when l.signal_age_min <= 60 then 0.5
            else 0.1
        end as freshness_score

    from latest l
    left join calendar_risk br on br.instrument_group = 'BR'
    left join calendar_risk ng on ng.instrument_group = 'NG'
    left join calendar_risk fx on fx.instrument_group = 'USDRUB'
    left join churn c on c.symbol = l.symbol
),

final as (
    select
        *,
        greatest(
            0.0,
            least(
                1.0,
                  0.30 * volatility_score
                + 0.25 * rvol_score
                + 0.20 * trend_efficiency_score
                + 0.10 * liquidity_score_v2
                + 0.10 * spread_quality_score
                + 0.15 * smart_money_score
                - 0.20 * event_risk_penalty
                - 0.25 * churn_penalty
            )
        ) as trade_priority_score,

        greatest(
            0.0,
            least(
                1.0,
                (
                    greatest(
                        0.0,
                        least(
                            1.0,
                              0.30 * volatility_score
                            + 0.25 * rvol_score
                            + 0.20 * trend_efficiency_score
                            + 0.10 * liquidity_score_v2
                            + 0.10 * spread_quality_score
                            + 0.15 * smart_money_score
                            - 0.20 * event_risk_penalty
                            - 0.25 * churn_penalty
                        )
                    )
                ) * freshness_score
            )
        ) as freshness_adjusted_score
    from scored
)

update market_opportunity_metrics m
set
    volatility_score = f.volatility_score,
    rvol_score = f.rvol_score,
    trend_efficiency_score = f.trend_efficiency_score,
    liquidity_score_v2 = f.liquidity_score_v2,
    spread_quality_score = f.spread_quality_score,
    event_risk_penalty = f.event_risk_penalty,
    churn_penalty = f.churn_penalty,
    trade_priority_score = f.trade_priority_score,
    signal_age_min = f.signal_age_min,
    freshness_score = f.freshness_score,
    freshness_adjusted_score = f.freshness_adjusted_score,
    freshness_reason =
        'age_min=' || round(f.signal_age_min::numeric, 2) ||
        ';freshness_score=' || round(f.freshness_score::numeric, 4) ||
        ';base_score=' || round(f.trade_priority_score::numeric, 4) ||
        ';freshness_adjusted_score=' || round(f.freshness_adjusted_score::numeric, 4),
    trade_priority_label =
        case
            when f.trade_priority_score >= 0.75 then '🔥 ТОП-приоритет'
            when f.trade_priority_score >= 0.55 then '🟢 Торговый кандидат'
            when f.trade_priority_score >= 0.35 then '🟡 Наблюдение'
            else '⚪ Низкий приоритет'
        end,
    trade_priority_reason =
        'volatility=' || round(f.volatility_score::numeric, 4) ||
        ';rvol=' || round(f.rvol_score::numeric, 4) ||
        ';trend=' || round(f.trend_efficiency_score::numeric, 4) ||
        ';liquidity=' || round(f.liquidity_score_v2::numeric, 4) ||
        ';spread=' || round(f.spread_quality_score::numeric, 4) ||
        ';smart_money=' || round(f.smart_money_score::numeric, 4) ||
        ';event_penalty=' || round(f.event_risk_penalty::numeric, 4) ||
        ';churn_penalty=' || round(f.churn_penalty::numeric, 4)
from final f
where m.id = f.id;
"""


REPORT_SQL = """
select
    symbol,
    asset_class,
    round(coalesce(trade_priority_score,0)::numeric, 6) as trade_priority_score,
    round(coalesce(freshness_adjusted_score,0)::numeric, 6) as freshness_adjusted_score,
    trade_priority_label,
    freshness_reason,
    trade_priority_reason,
    calculated_at
from market_opportunity_metrics
where calculated_at >= now() - interval '2 days'
order by trade_priority_score desc nulls last, calculated_at desc
limit 20;
"""


def main() -> int:
    database_url = os.environ["DATABASE_URL"]

    with psycopg2.connect(database_url) as conn:
        with conn.cursor() as cur:
            cur.execute(SQL)
            updated = cur.rowcount
            cur.execute(REPORT_SQL)
            rows = cur.fetchall()
        conn.commit()

    print(f"OK: market opportunity scoring v2 updated rows={updated}")
    for row in rows:
        print(row)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
