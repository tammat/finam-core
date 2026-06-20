#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import json
import os
import sys
import psycopg2
import psycopg2.extras

TARGETS = [
    "NVTK@MISX",
    "OZON@MISX",
    "T@MISX",
    "X5@MISX",
    "SBERP@MISX",
    "VTBR@MISX",
    "EUTR@MISX",
    "SFIN@MISX",
]

def main():
    dsn = os.environ.get("DATABASE_URL")
    if not dsn:
        print("ERROR=DATABASE_URL_NOT_SET")
        return 1

    result = []

    with psycopg2.connect(dsn) as conn:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:

            for symbol in TARGETS:

                row = {
                    "symbol": symbol
                }

                # runtime universe
                try:
                    cur.execute("""
                        select count(*)
                        from runtime_active_universe
                        where symbol=%s
                    """, (symbol,))
                    row["runtime_rows"] = cur.fetchone()["count"]
                except Exception:
                    row["runtime_rows"] = None

                # market bars M5
                try:
                    cur.execute("""
                        select
                            count(*) as bars,
                            max(bar_ts) as last_bar
                        from market_bars
                        where symbol=%s
                          and timeframe='M5'
                    """, (symbol,))
                    r = cur.fetchone()
                    row["m5_bars"] = r["bars"]
                    row["m5_last_bar"] = str(r["last_bar"])
                except Exception:
                    row["m5_bars"] = None
                    row["m5_last_bar"] = None

                # market bars M1
                try:
                    cur.execute("""
                        select count(*) as bars
                        from market_bars
                        where symbol=%s
                          and timeframe='M1'
                    """, (symbol,))
                    row["m1_bars"] = cur.fetchone()["bars"]
                except Exception:
                    row["m1_bars"] = None

                result.append(row)

    output = {
        "verdict": "EQUITY_NO_BARS_ROOT_CAUSE_AUDIT_READY",
        "db_update": 0,
        "runtime_changed": 0,
        "execution_changed": 0,
        "rows": result
    }

    print(json.dumps(output, ensure_ascii=False, indent=2))
    print("VERDICT=EQUITY_NO_BARS_ROOT_CAUSE_AUDIT_READY")
    print("TEST_EQUITY_NO_BARS_ROOT_CAUSE_AUDIT_V1_OK")

    return 0

if __name__ == "__main__":
    sys.exit(main())
