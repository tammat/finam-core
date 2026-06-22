#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import subprocess
import psycopg
from psycopg.rows import dict_row


def sh(cmd: list[str]) -> str:
    p = subprocess.run(cmd, capture_output=True, text=True)
    return (p.stdout or p.stderr or "").strip()


def main() -> int:
    dsn = os.getenv("DATABASE_URL")
    if not dsn:
        raise SystemExit("DATABASE_URL_NOT_SET")

    print("=== EQUITY_BARS_BACKFILL_APPLY_PLAN_V1 ===")
    print("mode=apply_plan_read_only")
    print("db_update=0")
    print("runtime_changed=0")
    print("execution_changed=0")
    print("telegram_send=0")

    candidates = [
        "src/scripts/research/backfill_equity_market_bars.py",
        "src/scripts/research/backfill_market_bars.py",
        "src/scripts/backfill_equity_market_bars.py",
        "src/scripts/load_market_bars.py",
        "src/scripts/research/load_equity_bars.py",
    ]

    existing = [x for x in candidates if os.path.exists(x)]

    grep_hits = sh([
        "bash",
        "-lc",
        "find src scripts -type f \\( -name '*.py' -o -name '*.sh' \\) "
        "| xargs grep -nE 'market_bars|FINAM.*BARS|equity.*bars|@MISX|M1|M5' "
        "| head -80"
    ])

    print(f"loader_candidates_found={len(existing)}")
    for x in existing:
        print(f"LOADER_CANDIDATE path={x}")

    if not existing:
        print("LOADER_CANDIDATE path=NOT_FOUND")

    with psycopg.connect(dsn, row_factory=dict_row) as conn:
        with conn.cursor() as cur:
            cur.execute("""
                with runtime_equities as (
                    select
                        symbol,
                        is_enabled,
                        strategy,
                        timeframe
                    from runtime_active_universe
                    where symbol like '%@MISX'
                ),
                bars as (
                    select
                        symbol,
                        count(*) filter (where timeframe='M1')::int as m1_bars,
                        count(*) filter (where timeframe='M5')::int as m5_bars,
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
                    coalesce(b.m1_bars, 0)::int as m1_bars,
                    coalesce(b.m5_bars, 0)::int as m5_bars,
                    b.last_bar_ts,
                    case
                        when coalesce(b.m1_bars, 0) + coalesce(b.m5_bars, 0) = 0
                            then 'BACKFILL_M1_M5_REQUIRED'
                        when b.last_bar_ts < now() - interval '1 day'
                            then 'REFRESH_TODAY_REQUIRED'
                        else 'NO_ACTION'
                    end as planned_action
                from runtime_equities re
                left join bars b on b.symbol = re.symbol
                order by planned_action, re.symbol
            """)
            rows = list(cur.fetchall())

    actions = 0

    for r in rows:
        if r["planned_action"] == "NO_ACTION":
            continue

        actions += 1
        symbol = r["symbol"]

        if r["planned_action"] == "BACKFILL_M1_M5_REQUIRED":
            scope = "full_backfill"
            from_arg = "2026-06-01"
        else:
            scope = "refresh_today"
            from_arg = "2026-06-22"

        print(
            "EQUITY_BACKFILL_PLAN_ROW "
            f"symbol={symbol} "
            f"action={r['planned_action']} "
            f"scope={scope} "
            f"timeframes=M1,M5 "
            f"from={from_arg} "
            f"m1={r['m1_bars']} "
            f"m5={r['m5_bars']} "
            f"last_bar_ts={r['last_bar_ts']}"
        )

        print(
            "EQUITY_BACKFILL_COMMAND "
            f"symbol={symbol} "
            f"cmd='PYTHONPATH=src RUNTIME_ALLOW_TRADING=0 EXECUTION_ENABLED=0 REAL_TRADING_ENABLED=0 "
            f"/opt/finam-core/venv/bin/python3 <LOADER_PATH> "
            f"--symbol {symbol} --timeframes M1,M5 --from {from_arg} --save'"
        )

    print(f"planned_actions={actions}")

    if grep_hits:
        print("LOADER_SEARCH_HINTS_START")
        print(grep_hits)
        print("LOADER_SEARCH_HINTS_END")

    if actions:
        print("VERDICT=EQUITY_BARS_BACKFILL_APPLY_PLAN_REQUIRED")
    else:
        print("VERDICT=EQUITY_BARS_BACKFILL_APPLY_PLAN_NO_ACTION")

    print("TEST_EQUITY_BARS_BACKFILL_APPLY_PLAN_V1_OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
