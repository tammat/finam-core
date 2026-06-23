#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import psycopg
from psycopg.rows import dict_row


def main() -> int:
    dsn = os.getenv("DATABASE_URL")
    if not dsn:
        raise SystemExit("DATABASE_URL_NOT_SET")

    print("=== EQUITY_NO_BARS_DIAGNOSTIC_V2 ===")
    print("mode=read_only")
    print("db_update=0")
    print("runtime_changed=0")
    print("execution_changed=0")
    print("telegram_send=0")

    with psycopg.connect(dsn, row_factory=dict_row) as conn:
        with conn.cursor() as cur:

            cur.execute("""
                select
                    symbol,
                    is_enabled
                from runtime_active_universe
                where symbol like '%@MISX'
                order by symbol
            """)

            runtime_rows = list(cur.fetchall())

            for r in runtime_rows:
                symbol = r["symbol"]

                cur.execute("""
                    select
                        timeframe,
                        count(*)::int as bars,
                        max(ts) as last_bar_ts
                    from market_bars
                    where symbol = %s
                    group by timeframe
                    order by timeframe
                """, (symbol,))

                bars_rows = list(cur.fetchall())

                m1 = 0
                m5 = 0
                h1 = 0
                last_bar = None

                for b in bars_rows:
                    if b["timeframe"] == "M1":
                        m1 = b["bars"]
                    elif b["timeframe"] == "M5":
                        m5 = b["bars"]
                    elif b["timeframe"] == "H1":
                        h1 = b["bars"]

                    if b["last_bar_ts"]:
                        if last_bar is None or b["last_bar_ts"] > last_bar:
                            last_bar = b["last_bar_ts"]

                status = "OK"

                if (m1 + m5 + h1) == 0:
                    status = "NO_BARS"

                print(
                    "EQUITY_BAR_ROW "
                    f"symbol={symbol} "
                    f"enabled={r['is_enabled']} "
                    f"m1={m1} "
                    f"m5={m5} "
                    f"h1={h1} "
                    f"last_bar_ts={last_bar} "
                    f"status={status}"
                )

            cur.execute("""
                select
                    count(*)::int
                from runtime_active_universe
                where symbol like '%@MISX'
            """)

            runtime_total = cur.fetchone()["count"]

    print(f"runtime_equities={runtime_total}")
    print("VERDICT=EQUITY_NO_BARS_DIAGNOSTIC_READY")
    print("TEST_EQUITY_NO_BARS_DIAGNOSTIC_V2_OK")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
