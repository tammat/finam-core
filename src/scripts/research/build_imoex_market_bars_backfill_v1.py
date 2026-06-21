#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import psycopg
from psycopg.rows import dict_row

def main() -> int:
    dsn = os.getenv("DATABASE_URL")
    if not dsn:
        raise SystemExit("DATABASE_URL_NOT_SET")

    print("=== IMOEX_MARKET_BARS_BACKFILL_V1 ===")
    print("mode=coverage_audit")
    print("db_update=0")
    print("runtime_changed=0")
    print("execution_changed=0")
    print("telegram_send=0")

    with psycopg.connect(dsn, row_factory=dict_row) as conn:
        with conn.cursor() as cur:
            cur.execute("""
                select
                    symbol,
                    timeframe,
                    count(*)::int as bars,
                    min(ts) as first_ts,
                    max(ts) as last_ts
                from market_bars
                where symbol = 'IMOEX'
                group by symbol, timeframe
                order by timeframe;
            """)
            rows = list(cur.fetchall())

    for r in rows:
        print(
            "IMOEX_BARS_ROW "
            f"symbol={r['symbol']} "
            f"timeframe={r['timeframe']} "
            f"bars={r['bars']} "
            f"first_ts={r['first_ts']} "
            f"last_ts={r['last_ts']}"
        )

    has_m5 = any(r["timeframe"] == "M5" and int(r["bars"] or 0) > 1000 for r in rows)

    print(f"rows_total={len(rows)}")
    print(f"has_m5={int(has_m5)}")

    if has_m5:
        print("VERDICT=IMOEX_MARKET_BARS_COVERAGE_READY")
    else:
        print("VERDICT=IMOEX_MARKET_BARS_BACKFILL_REQUIRED")

    print("TEST_IMOEX_MARKET_BARS_BACKFILL_V1_OK")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
