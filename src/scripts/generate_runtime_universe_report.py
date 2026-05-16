from __future__ import annotations

import csv
import os
from pathlib import Path

import psycopg2


SQL = """
select
    dw.symbol,
    dw.strategy,
    dw.regime,
    dw.score,
    dw.priority,
    dw.is_active,
    dw.updated_at,

    coalesce(pos.qty, 0) as position_qty,

    case
        when coalesce(pos.qty, 0) <> 0
        then true
        else false
    end as eviction_blocked_by_position

from dynamic_watchlist dw

left join lateral (
    select
        p.symbol,
        p.qty
    from positions p
    where p.symbol = dw.symbol
    limit 1
) pos on true

where dw.source = 'opportunity_scanner'

order by
    dw.is_active desc,
    dw.priority desc,
    dw.score desc nulls last,
    dw.symbol asc
"""


def main() -> int:

    database_url = os.getenv("DATABASE_URL")
    if not database_url:
        raise SystemExit("DATABASE_URL_NOT_SET")

    out_dir = Path("reports")
    out_dir.mkdir(parents=True, exist_ok=True)

    out_file = out_dir / "runtime_universe_state.tsv"

    conn = psycopg2.connect(database_url)

    try:
        with conn.cursor() as cur:
            cur.execute(SQL)
            rows = cur.fetchall()

            headers = [d[0] for d in cur.description]

        with out_file.open("w", encoding="utf-8", newline="") as f:
            writer = csv.writer(
                f,
                delimiter="\t",
            )

            writer.writerow(headers)

            for row in rows:
                writer.writerow(row)

    finally:
        conn.close()

    print(
        f"OK: runtime universe report generated rows={len(rows)} file={out_file}",
        flush=True,
    )

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
