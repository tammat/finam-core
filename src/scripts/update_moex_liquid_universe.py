from __future__ import annotations

import csv
import os
from pathlib import Path

import psycopg2


SQL = """
insert into moex_liquid_universe (
    symbol,
    asset_class,
    board,
    group_name,
    enabled,
    updated_at
)
values (%s, %s, %s, %s, %s, now())
on conflict (symbol)
do update set
    asset_class = excluded.asset_class,
    board = excluded.board,
    group_name = excluded.group_name,
    enabled = excluded.enabled,
    updated_at = now();
"""


def main() -> int:
    database_url = os.environ["DATABASE_URL"]
    path = Path(os.getenv("MOEX_LIQUID_UNIVERSE_TSV", "data/moex_liquid_universe.tsv"))

    rows = 0

    with psycopg2.connect(database_url) as conn:
        with conn.cursor() as cur:
            with path.open("r", encoding="utf-8", newline="") as f:
                reader = csv.DictReader(f, delimiter="\t")
                for row in reader:
                    cur.execute(
                        SQL,
                        (
                            row["symbol"],
                            row["asset_class"],
                            row["board"],
                            row["group_name"],
                            row["enabled"] == "1",
                        ),
                    )
                    rows += 1
        conn.commit()

    print(f"OK: moex liquid universe updated rows={rows}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
