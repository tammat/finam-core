#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import psycopg
from psycopg.rows import dict_row


def main() -> int:
    dsn = os.getenv("DATABASE_URL")
    if not dsn:
        raise SystemExit("DATABASE_URL_NOT_SET")

    print("=== EQUITY_BARS_COVERAGE_REPAIR_PLAN_V1 ===")
    print("mode=repair_plan_read_only")
    print("db_update=0")
    print("runtime_changed=0")
    print("execution_changed=0")
    print("telegram_send=0")

    with psycopg.connect(dsn, row_factory=dict_row) as conn:
        with conn.cursor() as cur:
            cur.execute("""
                with runtime_equities as (
                    select
                        symbol,
                        is_enabled,
                        strategy,
                        timeframe,
                        score,
                        priority
                    from runtime_active_universe
                    where symbol like '%@MISX'
                    order by symbol
                ),
                bars as (
                    select
                        symbol,
                        count(*) filter (where timeframe='M1')::int as m1_bars,
                        count(*) filter (where timeframe='M5')::int as m5_bars,
                        count(*) filter (where timeframe='H1')::int as h1_bars,
                        max(ts) as last_bar_ts
                    from market_bars
                    where symbol in (select symbol from runtime_equities)
                    group by symbol
                )
                select
                    re.symbol,
                    re.is_enabled,
                    re.strategy,
                    re.timeframe,
                    re.score,
                    re.priority,
                    coalesce(b.m1_bars, 0)::int as m1_bars,
                    coalesce(b.m5_bars, 0)::int as m5_bars,
                    coalesce(b.h1_bars, 0)::int as h1_bars,
                    b.last_bar_ts,
                    case
                        when coalesce(b.m1_bars, 0) + coalesce(b.m5_bars, 0) + coalesce(b.h1_bars, 0) = 0
                            then 'NO_BARS'
                        when b.last_bar_ts < now() - interval '1 day'
                            then 'STALE_BARS'
                        else 'OK_CURRENT'
                    end as coverage_status,
                    case
                        when coalesce(b.m1_bars, 0) + coalesce(b.m5_bars, 0) + coalesce(b.h1_bars, 0) = 0
                            then 'BACKFILL_M1_M5_REQUIRED'
                        when b.last_bar_ts < now() - interval '1 day'
                            then 'REFRESH_TODAY_REQUIRED'
                        else 'NO_ACTION'
                    end as planned_action
                from runtime_equities re
                left join bars b on b.symbol = re.symbol
                order by
                    case
                        when coalesce(b.m1_bars, 0) + coalesce(b.m5_bars, 0) + coalesce(b.h1_bars, 0) = 0 then 1
                        when b.last_bar_ts < now() - interval '1 day' then 2
                        else 3
                    end,
                    re.symbol
            """)
            rows = list(cur.fetchall())

    no_bars = 0
    stale = 0
    ok = 0

    for r in rows:
        status = r["coverage_status"]
        if status == "NO_BARS":
            no_bars += 1
        elif status == "STALE_BARS":
            stale += 1
        elif status == "OK_CURRENT":
            ok += 1

        print(
            "EQUITY_BARS_REPAIR_ROW "
            f"symbol={r['symbol']} "
            f"enabled={r['is_enabled']} "
            f"strategy={r['strategy']} "
            f"timeframe={r['timeframe']} "
            f"m1={r['m1_bars']} "
            f"m5={r['m5_bars']} "
            f"h1={r['h1_bars']} "
            f"last_bar_ts={r['last_bar_ts']} "
            f"coverage_status={status} "
            f"planned_action={r['planned_action']}"
        )

    print(f"runtime_equities={len(rows)}")
    print(f"ok_current={ok}")
    print(f"stale_bars={stale}")
    print(f"no_bars={no_bars}")

    if no_bars or stale:
        print("VERDICT=EQUITY_BARS_COVERAGE_REPAIR_PLAN_REQUIRED")
    else:
        print("VERDICT=EQUITY_BARS_COVERAGE_OK")

    print("TEST_EQUITY_BARS_COVERAGE_REPAIR_PLAN_V1_OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
