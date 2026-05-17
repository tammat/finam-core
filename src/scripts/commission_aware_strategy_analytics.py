from __future__ import annotations

import csv
import os
from pathlib import Path

import psycopg2


SQL = """
with base as (
    select
        symbol,
        coalesce(payload->>'strategy', payload->>'source', trade_source, origin, 'UNKNOWN') as strategy,
        coalesce(payload->>'institutional_flow_regime', 'UNKNOWN') as institutional_regime,
        coalesce(payload->>'adaptive_position_multiplier', '1.00') as adaptive_multiplier,
        coalesce(qty, 0) as qty,
        coalesce(price, 0) as price,
        coalesce(commission, 0) as actual_commission,
        abs(coalesce(qty, 0) * coalesce(price, 0)) as notional
    from trades
),

costs as (
    select
        *,
        case
            when actual_commission > 0 then actual_commission
            else notional * ({commission_bps} / 10000.0)
        end as estimated_commission,

        notional * ({slippage_bps} / 10000.0) as estimated_slippage
    from base
),

agg as (
    select
        symbol,
        strategy,
        institutional_regime,
        adaptive_multiplier,

        count(*) as trades,
        round(avg(qty)::numeric, 6) as avg_qty,
        round(sum(notional)::numeric, 2) as turnover,

        round(sum(estimated_commission)::numeric, 2) as commission_cost,
        round(sum(estimated_slippage)::numeric, 2) as slippage_cost,
        round((sum(estimated_commission) + sum(estimated_slippage))::numeric, 2) as total_cost,

        round(avg(estimated_commission + estimated_slippage)::numeric, 4) as avg_cost_per_trade,

        round(
            case
                when sum(notional) > 0
                then ((sum(estimated_commission) + sum(estimated_slippage)) / sum(notional) * 100)::numeric
                else 0
            end,
            6
        ) as cost_pct_of_turnover

    from costs
    group by 1,2,3,4
)

select
    symbol as "Инструмент",
    strategy as "Стратегия / источник",
    institutional_regime as "Режим крупного капитала",
    adaptive_multiplier as "Мультипликатор позиции",
    trades as "Количество сделок",
    avg_qty as "Средний объём",
    turnover as "Оборот",
    commission_cost as "Комиссии",
    slippage_cost as "Оценочное проскальзывание",
    total_cost as "Итого издержки",
    avg_cost_per_trade as "Издержки на сделку",
    cost_pct_of_turnover as "Издержки, % оборота"
from agg
order by "Итого издержки" desc nulls last;
"""


def main() -> int:
    database_url = os.environ["DATABASE_URL"]

    commission_bps = float(os.getenv("ANALYTICS_COMMISSION_BPS", "2.0"))
    slippage_bps = float(os.getenv("ANALYTICS_SLIPPAGE_BPS", "3.0"))

    out_dir = Path("reports/strategy_analytics")
    out_dir.mkdir(parents=True, exist_ok=True)

    out_file = out_dir / "commission_aware_strategy_analytics.tsv"

    with psycopg2.connect(database_url) as conn:
        with conn.cursor() as cur:
            sql = SQL.format(
                commission_bps=commission_bps,
                slippage_bps=slippage_bps,
            )
            cur.execute(sql)
            rows = cur.fetchall()
            headers = [desc[0] for desc in cur.description]

    with out_file.open("w", encoding="utf-8", newline="") as f:
        writer = csv.writer(f, delimiter="\t")
        writer.writerow(headers)
        writer.writerows(rows)

    print(
        f"OK: commission-aware analytics rows={len(rows)} "
        f"file={out_file} commission_bps={commission_bps} slippage_bps={slippage_bps}",
        flush=True,
    )

    for row in rows[:20]:
        print(row)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
