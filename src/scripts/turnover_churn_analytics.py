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
        count(*) as trades,
        sum(abs(coalesce(qty, 0) * coalesce(price, 0))) as turnover
    from trades
    group by 1,2
),

metrics as (
    select
        symbol,
        strategy,
        trades,
        round(turnover::numeric, 2) as turnover,

        round(
            case
                when turnover > 0 then (trades / turnover * 1000)::numeric
                else 0
            end,
            6
        ) as trades_per_1000_turnover,

        case
            when turnover <= 0 then '⚪ Нет оборота'
            when trades / turnover * 1000 >= 50 then '🔴 Критический churn'
            when trades / turnover * 1000 >= 10 then '🟠 Высокий churn'
            when trades / turnover * 1000 >= 3 then '🟡 Средний churn'
            else '🟢 Нормальная частота'
        end as churn_status

    from base
)

select
    symbol as "Инструмент",
    strategy as "Стратегия / источник",
    trades as "Количество сделок",
    turnover as "Оборот",
    trades_per_1000_turnover as "Сделок на 1000 ₽ оборота",
    churn_status as "Статус churn"
from metrics
order by trades_per_1000_turnover desc nulls last;
"""


def main() -> int:
    database_url = os.environ["DATABASE_URL"]
    out_dir = Path("reports/strategy_analytics")
    out_dir.mkdir(parents=True, exist_ok=True)

    out_file = out_dir / "turnover_churn_analytics.tsv"

    with psycopg2.connect(database_url) as conn:
        with conn.cursor() as cur:
            cur.execute(SQL)
            rows = cur.fetchall()
            headers = [desc[0] for desc in cur.description]

    with out_file.open("w", encoding="utf-8", newline="") as f:
        writer = csv.writer(f, delimiter="\t")
        writer.writerow(headers)
        writer.writerows(rows)

    print(f"OK: turnover churn analytics rows={len(rows)} file={out_file}")

    for row in rows[:20]:
        print(row)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
