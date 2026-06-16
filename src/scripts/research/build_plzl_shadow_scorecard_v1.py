#!/usr/bin/env python3
from __future__ import annotations

import os
import psycopg2
import psycopg2.extras

SQL = """
select
    count(*) as total_signals,
    count(*) filter (where side='BUY') as buy_signals,
    count(*) filter (where side='SELL') as sell_signals,
    count(*) filter (
        where created_at >= now() - interval '7 days'
    ) as signals_last_7d,
    count(*) filter (
        where created_at >= now() - interval '30 days'
    ) as signals_last_30d,
    min(signal_ts) as first_signal,
    max(signal_ts) as last_signal,
    count(distinct signal_ts::date) as active_days
from plzl_shadow_accumulation_v1
where symbol='PLZL@MISX';
"""

def main() -> int:
    print("=== PLZL SHADOW SCORECARD V1 ===")
    print("mode=shadow_only")
    print("runtime_allow=0")
    print("execution_enabled=0")

    with psycopg2.connect(os.environ["DATABASE_URL"]) as conn:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute(SQL)
            row = cur.fetchone()

    total = int(row["total_signals"] or 0)
    active_days = int(row["active_days"] or 0)

    avg_per_day = (
        round(total / active_days, 4)
        if active_days > 0
        else 0.0
    )

    print(
        "PLZL_SCORECARD_ROW "
        f"total_signals={total} "
        f"buy_signals={int(row['buy_signals'] or 0)} "
        f"sell_signals={int(row['sell_signals'] or 0)} "
        f"signals_last_7d={int(row['signals_last_7d'] or 0)} "
        f"signals_last_30d={int(row['signals_last_30d'] or 0)} "
        f"active_days={active_days} "
        f"avg_signals_per_day={avg_per_day} "
        f"first_signal={row['first_signal']} "
        f"last_signal={row['last_signal']} "
        "runtime_allow=0 "
        "execution_enabled=0"
    )

    print("PLZL_SHADOW_SCORECARD_V1_OK")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
