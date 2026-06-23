#!/usr/bin/env python3

from decimal import Decimal
import os
import psycopg
from psycopg.rows import dict_row

TABLE = "analytics_futures_rs_bottom_paper_observation_v1"

ALLOWED = (
    "GLU6@RTSX",
    "GDU6@RTSX",
    "NGM6@RTSX",
    "BRN6@RTSX",
    "USDRUBF@RTSX",
)

EXCLUDED_HOURS = (12, 13, 14)

def d(v):
    return Decimal(str(v or 0))

db = os.environ["DATABASE_URL"]

print("=== RS_BOTTOM_SESSION_FILTER_STABILITY_V1 ===")
print("mode=read_only")
print("db_update=0")
print("runtime_changed=0")
print("execution_changed=0")
print("real_trading_enabled=0")

with psycopg.connect(db, row_factory=dict_row) as conn:
    with conn.cursor() as cur:

        cur.execute(f"""
        with src as (
            select
                source_ts::date as trade_day,
                symbol,
                return_pct,
                status
            from {TABLE}
            where selection='BOTTOM3'
              and filter_name='COMPRESSION_RANGE'
              and symbol = any(%s)
              and extract(hour from source_ts at time zone 'Europe/Moscow')::int <> all(%s)
              and status in ('SUCCESS','FAILURE')
        )
        select
            trade_day,
            count(*) completed,
            avg(return_pct) expectancy,
            sum(greatest(return_pct,0))
            /
            nullif(abs(sum(least(return_pct,0))),0) pf
        from src
        group by trade_day
        order by trade_day;
        """, (list(ALLOWED), list(EXCLUDED_HOURS)))

        days = cur.fetchall()

        positive_days = 0
        total_days = 0

        print("\n=== BY_DAY ===")
        for r in days:
            total_days += 1
            pf = d(r["pf"])
            exp = d(r["expectancy"])

            if pf > 1 and exp > 0:
                positive_days += 1

            print(
                f"DAY_ROW day={r['trade_day']} "
                f"completed={r['completed']} "
                f"expectancy={exp} pf={pf}"
            )

        cur.execute(f"""
        with src as (
            select
                symbol,
                return_pct,
                status
            from {TABLE}
            where selection='BOTTOM3'
              and filter_name='COMPRESSION_RANGE'
              and symbol = any(%s)
              and extract(hour from source_ts at time zone 'Europe/Moscow')::int <> all(%s)
              and status in ('SUCCESS','FAILURE')
        )
        select
            symbol,
            count(*) completed,
            avg(return_pct) expectancy,
            sum(greatest(return_pct,0))
            /
            nullif(abs(sum(least(return_pct,0))),0) pf
        from src
        group by symbol
        order by pf desc nulls last;
        """, (list(ALLOWED), list(EXCLUDED_HOURS)))

        rows = cur.fetchall()

        positive_symbols = 0

        print("\n=== BY_SYMBOL ===")
        for r in rows:
            pf = d(r["pf"])
            exp = d(r["expectancy"])

            if pf > 1 and exp > 0:
                positive_symbols += 1

            print(
                f"SYMBOL_ROW symbol={r['symbol']} "
                f"completed={r['completed']} "
                f"expectancy={exp} "
                f"pf={pf}"
            )

print("\nSTABILITY_SUMMARY")
print(f"positive_days={positive_days}")
print(f"total_days={total_days}")
print(f"positive_symbols={positive_symbols}")

if positive_days >= 2 and positive_symbols >= 3:
    verdict = "RS_BOTTOM_SESSION_FILTER_STABILITY_CONFIRMED"
else:
    verdict = "RS_BOTTOM_SESSION_FILTER_STABILITY_WEAK"

print(f"VERDICT={verdict}")
