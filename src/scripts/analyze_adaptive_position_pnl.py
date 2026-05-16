from __future__ import annotations

import os
import csv
from pathlib import Path

import psycopg2


SQL = """
with base as (
    select
        symbol,

        coalesce(
            nullif(payload->>'adaptive_position_multiplier', '')::numeric,
            1.0
        ) as multiplier,

        coalesce(qty, 0) as qty,
        coalesce(price, 0) as price,
        coalesce(qty, 0) * coalesce(price, 0) as notional

    from trades
),

agg as (
    select
        round(multiplier::numeric, 2) as multiplier,

        count(*) as trades,

        round(avg(qty)::numeric, 6) as avg_qty,

        round(sum(notional)::numeric, 2) as total_notional,

        round(avg(notional)::numeric, 2) as avg_notional

    from base
    group by 1
)

select
    multiplier,
    trades,
    avg_qty,
    total_notional,
    avg_notional
from agg
order by multiplier;
"""


def main() -> int:
    database_url = os.environ["DATABASE_URL"]

    out_dir = Path("reports")
    out_dir.mkdir(parents=True, exist_ok=True)

    out_file = out_dir / "adaptive_position_pnl.tsv"

    conn = psycopg2.connect(database_url)

    with conn:
        with conn.cursor() as cur:
            cur.execute(SQL)
            rows = cur.fetchall()

    with out_file.open("w", encoding="utf-8", newline="") as f:
        writer = csv.writer(f, delimiter="\t")

        writer.writerow([
            "multiplier",
            "trades",
            "avg_qty",
            "total_notional",
            "avg_notional",
        ])

        writer.writerows(rows)

    print(
        f"OK: adaptive position pnl report rows={len(rows)} file={out_file}",
        flush=True,
    )

    for r in rows:
        print(r)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
