from __future__ import annotations

import csv
import os
from pathlib import Path

import psycopg2


SQL = """
with base as (
    select
        coalesce(payload->>'requested_symbol', symbol) as requested_symbol,

        coalesce(
            payload->>'execution_symbol',
            symbol
        ) as execution_symbol,

        coalesce(
            payload->>'continuous_symbol',
            'NONE'
        ) as continuous_symbol,

        count(*) as trades,

        round(avg(qty)::numeric, 6) as avg_qty,

        round(sum(qty * price)::numeric, 2) as total_notional

    from trades
    group by 1,2,3
)

select
    requested_symbol,
    execution_symbol,
    continuous_symbol,
    trades,
    avg_qty,
    total_notional
from base
order by total_notional desc nulls last;
"""


def main() -> int:
    database_url = os.environ["DATABASE_URL"]

    out_dir = Path("reports")
    out_dir.mkdir(parents=True, exist_ok=True)

    out_file = out_dir / "execution_lineage_report.tsv"

    conn = psycopg2.connect(database_url)

    with conn:
        with conn.cursor() as cur:
            cur.execute(SQL)
            rows = cur.fetchall()

    with out_file.open("w", encoding="utf-8", newline="") as f:
        writer = csv.writer(f, delimiter="\t")

        writer.writerow([
            "requested_symbol",
            "execution_symbol",
            "continuous_symbol",
            "trades",
            "avg_qty",
            "total_notional",
        ])

        writer.writerows(rows)

    print(
        f"OK: execution lineage report rows={len(rows)} file={out_file}",
        flush=True,
    )

    for row in rows[:20]:
        print(row)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
