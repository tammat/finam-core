#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import psycopg
from psycopg.rows import dict_row

def main():
    dsn = os.getenv("DATABASE_URL")
    if not dsn:
        raise SystemExit("DATABASE_URL_NOT_SET")

    print("=== RS_BOTTOM_FORWARD_ACCUMULATION_V1 ===")
    print("mode=read_only")
    print("db_update=0")
    print("runtime_changed=0")
    print("execution_changed=0")
    print("telegram_send=0")

    with psycopg.connect(dsn, row_factory=dict_row) as conn:
        with conn.cursor() as cur:

            cur.execute("""
                select
                    selection,
                    filter_name,
                    signals_total,
                    waiting,
                    success,
                    failure,
                    completed,
                    profit_factor_forward,
                    profit_factor_historical,
                    avg_return_pct
                from analytics_futures_rs_bottom_forward_scorecard_v1
                order by profit_factor_historical desc nulls last
            """)

            rows = list(cur.fetchall())

    completed_total = 0

    for r in rows:
        completed_total += int(r["completed"] or 0)

        print(
            "RS_BOTTOM_ACCUMULATION_ROW "
            f"selection={r['selection']} "
            f"filter={r['filter_name']} "
            f"signals_total={r['signals_total']} "
            f"waiting={r['waiting']} "
            f"success={r['success']} "
            f"failure={r['failure']} "
            f"completed={r['completed']} "
            f"pf_forward={r['profit_factor_forward']} "
            f"pf_historical={r['profit_factor_historical']}"
        )

    print(f"completed_total={completed_total}")

    if completed_total >= 30:
        print("VERDICT=FORWARD_DECISION_READY")
    elif completed_total >= 10:
        print("VERDICT=FORWARD_EARLY_REVIEW")
    else:
        print("VERDICT=FORWARD_ACCUMULATION")

    print("TEST_RS_BOTTOM_FORWARD_ACCUMULATION_V1_OK")

if __name__ == "__main__":
    main()
