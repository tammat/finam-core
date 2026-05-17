from __future__ import annotations

import csv
import os
from pathlib import Path

import psycopg2


SQL = """
select
    coalesce(payload->>'adaptive_regime_action', '❔ Нет данных') as "Решение adaptive regime",
    coalesce(payload->>'institutional_flow_regime_ru', '❔ Нет данных') as "Режим крупного капитала",
    count(*) as "Количество сделок",
    round(avg(qty)::numeric, 6) as "Средний объём",
    round(sum(abs(qty * price))::numeric, 2) as "Оборот",
    round(sum(coalesce(commission, 0))::numeric, 2) as "Комиссии",
    round(avg(coalesce((payload->>'adaptive_regime_multiplier')::numeric, 1.0))::numeric, 6)
        as "Средний множитель режима",
    max(ts) as "Последняя сделка"
from trades
group by 1,2
order by "Количество сделок" desc, "Оборот" desc nulls last;
"""


def main() -> int:
    database_url = os.environ["DATABASE_URL"]

    out_dir = Path("reports/strategy_analytics")
    out_dir.mkdir(parents=True, exist_ok=True)

    out_file = out_dir / "adaptive_regime_decision_analytics.tsv"

    with psycopg2.connect(database_url) as conn:
        with conn.cursor() as cur:
            cur.execute(SQL)
            rows = cur.fetchall()
            headers = [desc[0] for desc in cur.description]

    with out_file.open("w", encoding="utf-8", newline="") as f:
        writer = csv.writer(f, delimiter="\t")
        writer.writerow(headers)
        writer.writerows(rows)

    print(f"OK: adaptive regime decision analytics rows={len(rows)} file={out_file}")
    for row in rows[:20]:
        print(row)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
