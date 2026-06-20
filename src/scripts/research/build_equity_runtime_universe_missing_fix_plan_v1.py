#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import json
import os
import sys
import psycopg2
import psycopg2.extras

REMOVE_SYMBOLS = ["EUTR@MISX"]
REVIEW_SYMBOLS = ["SBERP@MISX", "VTBR@MISX", "SFIN@MISX"]

def main() -> int:
    dsn = os.environ.get("DATABASE_URL")
    if not dsn:
        print("ERROR=DATABASE_URL_NOT_SET")
        return 1

    rows = []

    with psycopg2.connect(dsn) as conn:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            for symbol in REMOVE_SYMBOLS + REVIEW_SYMBOLS:
                cur.execute("""
                    select count(*) as rows
                    from runtime_active_universe
                    where symbol = %s
                """, (symbol,))
                runtime_rows = int(cur.fetchone()["rows"] or 0)

                cur.execute("""
                    select count(*) as rows, max(created_at) as last_seen
                    from analytics_multi_asset_breakout_row_v1
                    where symbol = %s
                """, (symbol,))
                hist = cur.fetchone()

                action = "REMOVE_FROM_ACTIVE_RESEARCH_SCOPE" if symbol in REMOVE_SYMBOLS else "REVIEW_RUNTIME_UNIVERSE_MISSING"

                rows.append({
                    "symbol": symbol,
                    "runtime_rows": runtime_rows,
                    "history_rows": int(hist["rows"] or 0),
                    "history_last_seen": None if hist["last_seen"] is None else str(hist["last_seen"]),
                    "planned_action": action,
                })

    out = {
        "verdict": "EQUITY_RUNTIME_UNIVERSE_MISSING_FIX_PLAN_READY",
        "mode": "plan_only",
        "db_update": 0,
        "runtime_changed": 0,
        "execution_changed": 0,
        "remove_symbols": REMOVE_SYMBOLS,
        "review_symbols": REVIEW_SYMBOLS,
        "rows": rows,
    }

    print(json.dumps(out, ensure_ascii=False, indent=2))
    print("VERDICT=EQUITY_RUNTIME_UNIVERSE_MISSING_FIX_PLAN_READY")
    print("TEST_EQUITY_RUNTIME_UNIVERSE_MISSING_FIX_PLAN_V1_OK")
    return 0

if __name__ == "__main__":
    sys.exit(main())
