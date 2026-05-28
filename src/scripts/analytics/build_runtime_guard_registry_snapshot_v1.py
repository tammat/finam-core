from __future__ import annotations

import os
import psycopg
from psycopg.rows import dict_row

from finam_core.analytics.statistics_repository import build_psycopg_url


def main() -> int:
    database_url = os.getenv("DATABASE_URL") or build_psycopg_url()

    with psycopg.connect(database_url, row_factory=dict_row) as conn:
        with conn.cursor() as cur:
            cur.execute("""
            select
              symbol,
              strategy,
              timeframe,
              guard_decision,
              runtime_soft_blocked,
              count(*) as signals,
              count(*) filter (where guard_matched is true) as matched,
              round(avg(profit_factor)::numeric, 4) as avg_pf,
              round(avg(expectancy)::numeric, 6) as avg_expectancy,
              max(ts) as last_ts
            from runtime_guard_signal_registry_v1
            group by
              symbol,
              strategy,
              timeframe,
              guard_decision,
              runtime_soft_blocked
            order by
              signals desc,
              symbol,
              strategy;
            """)
            rows = cur.fetchall()

    print("RUNTIME_GUARD_REGISTRY_SNAPSHOT_V1")
    for r in rows:
        print(
            "RUNTIME_GUARD_REGISTRY_ROW "
            f"symbol={r['symbol']} "
            f"strategy={r['strategy']} "
            f"timeframe={r['timeframe']} "
            f"decision={r['guard_decision']} "
            f"soft_blocked={r['runtime_soft_blocked']} "
            f"signals={r['signals']} "
            f"matched={r['matched']} "
            f"avg_pf={r['avg_pf']} "
            f"avg_expectancy={r['avg_expectancy']} "
            f"last_ts={r['last_ts']}",
            flush=True,
        )

    print(f"RUNTIME_GUARD_REGISTRY_SNAPSHOT_V1_OK rows={len(rows)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
