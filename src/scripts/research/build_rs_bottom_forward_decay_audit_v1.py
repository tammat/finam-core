#!/usr/bin/env python3
import os, psycopg2

print("=== RS_BOTTOM_FORWARD_DECAY_AUDIT_V1 ===")
print("mode=read_only")
print("db_update=0")
print("runtime_changed=0")
print("execution_changed=0")

dsn=os.getenv("DATABASE_URL")
if not dsn:
    print("VERDICT=DATABASE_URL_NOT_SET")
    raise SystemExit(1)

with psycopg2.connect(dsn) as conn:
    with conn.cursor() as cur:
        cur.execute("""
        select selection, filter_name, signals_total, waiting, success, failure,
               completed, profit_factor_forward, avg_return_pct, verdict
        from analytics_futures_rs_bottom_forward_scorecard_v1
        order by completed desc, selection, filter_name
        """)
        for r in cur.fetchall():
            print(
                "FORWARD_ROW "
                f"selection={r[0]} filter={r[1]} total={r[2]} waiting={r[3]} "
                f"success={r[4]} failure={r[5]} completed={r[6]} "
                f"pf_forward={r[7]} avg_return_pct={r[8]} verdict={r[9]}"
            )

print("VERDICT=RS_BOTTOM_FORWARD_DECAY_AUDIT_READY")
print("TEST_RS_BOTTOM_FORWARD_DECAY_AUDIT_V1_OK")
