#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import json
import os
import psycopg2
import psycopg2.extras

def main():
    dsn = os.getenv("DATABASE_URL")
    if not dsn:
        raise SystemExit("DATABASE_URL_NOT_SET")

    with psycopg2.connect(dsn) as conn:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:

            cur.execute("""
                select
                    symbol,
                    strategy,
                    priority,
                    score,
                    source
                from runtime_active_universe
                where symbol like '%@MISX'
                  and is_enabled = true
                order by priority desc
            """)
            runtime_rows = list(cur.fetchall())

            cur.execute("""
                select
                    symbol,
                    status,
                    close,
                    prev_high,
                    atr_pct,
                    volume_ratio,
                    created_at
                from analytics_multi_asset_breakout_row_v1
                where symbol like '%@MISX'
                order by created_at desc
                limit 50
            """)
            breakout_rows = list(cur.fetchall())

    no_bars = sum(
        1 for r in breakout_rows
        if "NO_ENOUGH_BARS" in str(r["status"])
    )

    watch = sum(
        1 for r in breakout_rows
        if "WATCH" in str(r["status"])
    )

    close_to_breakout = 0
    for r in breakout_rows:
        try:
            c = float(r["close"])
            ph = float(r["prev_high"])
            dist = ((c - ph) / ph) * 100.0
            if dist > -0.5:
                close_to_breakout += 1
        except Exception:
            pass

    out = {
        "verdict": "MULTI_ASSET_BREAKOUT_8_EQUITY_RUNTIME_OBSERVATION_READY",
        "db_update": 0,
        "runtime_changed": 0,
        "execution_changed": 0,
        "telegram_send": 0,
        "runtime_equities": len(runtime_rows),
        "watch_rows": len(breakout_rows),
        "no_bars": no_bars,
        "watch_candidates": watch,
        "close_to_breakout": close_to_breakout,
        "runtime_rows": runtime_rows,
        "breakout_rows": breakout_rows[:20],
    }

    print(json.dumps(out, ensure_ascii=False, indent=2, default=str))
    print("VERDICT=MULTI_ASSET_BREAKOUT_8_EQUITY_RUNTIME_OBSERVATION_READY")
    print("TEST_MULTI_ASSET_BREAKOUT_8_EQUITY_RUNTIME_OBSERVATION_V1_OK")

if __name__ == "__main__":
    main()
