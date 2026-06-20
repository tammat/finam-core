#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import json
import os
import sys
import psycopg2
import psycopg2.extras

TARGETS = [
    "EUTR@MISX",
    "SBERP@MISX",
    "VTBR@MISX",
    "SFIN@MISX",
]

def table_exists(cur, table_name: str) -> bool:
    cur.execute(
        """
        select to_regclass(%s) as regclass
        """,
        (table_name,)
    )
    row = cur.fetchone()
    return row is not None and row.get("regclass") is not None

def main() -> int:
    dsn = os.environ.get("DATABASE_URL")
    if not dsn:
        print("ERROR=DATABASE_URL_NOT_SET")
        return 1

    rows = []

    with psycopg2.connect(dsn) as conn:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:

            has_dynamic = table_exists(cur, "dynamic_watchlist")

            for symbol in TARGETS:

                row = {
                    "symbol": symbol,
                    "dynamic_watchlist": None,
                    "runtime_active_universe": None,
                    "history_rows": 0,
                    "planned_action": "REVIEW"
                }

                if has_dynamic:
                    try:
                        cur.execute("""
                            select *
                            from dynamic_watchlist
                            where symbol=%s
                            limit 1
                        """, (symbol,))
                        dw = cur.fetchone()
                        row["dynamic_watchlist"] = dw is not None
                    except Exception as exc:
                        row["dynamic_watchlist_error"] = str(exc)

                try:
                    cur.execute("""
                        select count(*)::int as rows
                        from runtime_active_universe
                        where symbol=%s
                    """, (symbol,))
                    row["runtime_active_universe"] = int(cur.fetchone()["rows"] or 0)
                except Exception as exc:
                    row["runtime_error"] = str(exc)

                cur.execute("""
                    select count(*)::int as rows
                    from analytics_multi_asset_breakout_row_v1
                    where symbol=%s
                """, (symbol,))
                row["history_rows"] = int(cur.fetchone()["rows"] or 0)

                if row["dynamic_watchlist"] is False:
                    row["planned_action"] = "ADD_TO_DYNAMIC_WATCHLIST_PLAN"
                elif row["dynamic_watchlist"] is True and row["runtime_active_universe"] == 0:
                    row["planned_action"] = "ALLOCATOR_SELECTION_REVIEW"
                else:
                    row["planned_action"] = "NO_ACTION"

                rows.append(row)

    summary = {}
    for r in rows:
        summary[r["planned_action"]] = summary.get(r["planned_action"], 0) + 1

    out = {
        "verdict": "EQUITY_RUNTIME_UNIVERSE_REINSTATE_PLAN_READY",
        "mode": "plan_only",
        "db_update": 0,
        "runtime_changed": 0,
        "execution_changed": 0,
        "telegram_send": 0,
        "summary": summary,
        "rows": rows,
    }

    print(json.dumps(out, ensure_ascii=False, indent=2))
    print("VERDICT=EQUITY_RUNTIME_UNIVERSE_REINSTATE_PLAN_READY")
    print("TEST_EQUITY_RUNTIME_UNIVERSE_REINSTATE_PLAN_V1_OK")

    return 0

if __name__ == "__main__":
    sys.exit(main())
