from __future__ import annotations

import csv
import os
from pathlib import Path

import psycopg2


UPSERT_SQL = """
insert into market_event_calendar (
    event_time,
    event_type,
    instrument_group,
    event_name,
    severity,
    source,
    pre_event_block_min,
    pre_event_reduce_min,
    is_active,
    raw_json,
    updated_at
)
values (
    %s, %s, %s, %s, %s, %s, %s, %s, true, %s::jsonb, now()
)
on conflict do nothing;
"""


def main() -> int:
    database_url = os.environ["DATABASE_URL"]
    path = Path(os.getenv("MARKET_EVENT_CALENDAR_TSV", "data/market_event_calendar.tsv"))

    if not path.exists():
        raise FileNotFoundError(path)

    inserted = 0

    with psycopg2.connect(database_url) as conn:
        with conn.cursor() as cur:
            with path.open("r", encoding="utf-8", newline="") as f:
                reader = csv.DictReader(f, delimiter="\t")

                for row in reader:
                    cur.execute(
                        UPSERT_SQL,
                        (
                            row["event_time"],
                            row["event_type"],
                            row["instrument_group"],
                            row["event_name"],
                            row["severity"],
                            row["source"],
                            int(row["pre_event_block_min"]),
                            int(row["pre_event_reduce_min"]),
                            "{}",
                        ),
                    )
                    inserted += cur.rowcount

        conn.commit()

    print(f"OK: market event calendar updated rows_inserted={inserted} file={path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
