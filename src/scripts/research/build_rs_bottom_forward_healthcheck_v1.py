#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import subprocess
import sys
from decimal import Decimal

import psycopg
from psycopg.rows import dict_row


SCORECARD_SCRIPT = "src/scripts/research/build_rs_bottom_forward_scorecard_v1.py"


def dec(v):
    if v is None:
        return None
    return Decimal(str(v))


def pct(source, future):
    source = dec(source)
    future = dec(future)
    if source is None or future is None or source == 0:
        return None
    return (future - source) / source * Decimal("100")


def update_waiting_rows(cur) -> tuple[int, int, int]:
    cur.execute("""
        select
            id,
            symbol,
            source_ts,
            source_close,
            horizon_min
        from analytics_futures_rs_bottom_paper_observation_v1
        where status = 'WAITING'
        order by source_ts
    """)
    rows = list(cur.fetchall())

    checked = 0
    updated = 0
    still_waiting = 0

    for r in rows:
        checked += 1

        cur.execute("""
            select ts, close
            from market_bars
            where symbol = %s
              and timeframe = 'M5'
              and ts >= (%s + (%s::text || ' minutes')::interval)
            order by ts asc
            limit 1
        """, (r["symbol"], r["source_ts"], int(r["horizon_min"])))
        future = cur.fetchone()

        if not future:
            still_waiting += 1
            continue

        ret = pct(r["source_close"], future["close"])
        if ret is None:
            still_waiting += 1
            continue

        status = "SUCCESS" if ret > 0 else "FAILURE"

        cur.execute("""
            update analytics_futures_rs_bottom_paper_observation_v1
            set
                future_ts = %s,
                future_close = %s,
                return_pct = %s,
                status = %s
            where id = %s
              and status = 'WAITING'
        """, (
            future["ts"],
            future["close"],
            ret,
            status,
            r["id"],
        ))

        if cur.rowcount:
            updated += 1

    return checked, updated, still_waiting


def run_scorecard() -> bool:
    env = os.environ.copy()
    env["PYTHONPATH"] = "src"
    env["RUNTIME_ALLOW_TRADING"] = "0"
    env["EXECUTION_ENABLED"] = "0"
    env["REAL_TRADING_ENABLED"] = "0"

    result = subprocess.run(
        [sys.executable, SCORECARD_SCRIPT],
        cwd="/opt/finam-core",
        env=env,
        text=True,
        check=False,
    )

    return result.returncode == 0


def main() -> int:
    dsn = os.getenv("DATABASE_URL")
    if not dsn:
        raise SystemExit("DATABASE_URL_NOT_SET")

    print("=== RS_BOTTOM_FORWARD_HEALTHCHECK_V1 ===")
    print("mode=healthcheck")
    print("db_update=1")
    print("runtime_changed=0")
    print("execution_changed=0")
    print("telegram_send=0")

    with psycopg.connect(dsn, row_factory=dict_row) as conn:
        with conn.cursor() as cur:
            checked, updated, still_waiting = update_waiting_rows(cur)
            conn.commit()

    scorecard_ok = run_scorecard()

    with psycopg.connect(dsn, row_factory=dict_row) as conn:
        with conn.cursor() as cur:
            cur.execute("""
                select
                    count(*)::int as rows_total,
                    count(*) filter (where status='WAITING')::int as waiting,
                    count(*) filter (where status='SUCCESS')::int as success,
                    count(*) filter (where status='FAILURE')::int as failure
                from analytics_futures_rs_bottom_paper_observation_v1
            """)
            summary = cur.fetchone()

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
                    verdict
                from analytics_futures_rs_bottom_forward_scorecard_v1
                order by profit_factor_historical desc nulls last
            """)
            score_rows = list(cur.fetchall())

    print(f"waiting_checked={checked}")
    print(f"waiting_updated={updated}")
    print(f"still_waiting={still_waiting}")
    print(f"scorecard_ok={int(scorecard_ok)}")
    print(f"rows_total={summary['rows_total']}")
    print(f"rows_waiting={summary['waiting']}")
    print(f"rows_success={summary['success']}")
    print(f"rows_failure={summary['failure']}")

    for r in score_rows:
        print(
            "RS_BOTTOM_FORWARD_HEALTH_ROW "
            f"selection={r['selection']} "
            f"filter={r['filter_name']} "
            f"signals_total={r['signals_total']} "
            f"waiting={r['waiting']} "
            f"success={r['success']} "
            f"failure={r['failure']} "
            f"completed={r['completed']} "
            f"pf_forward={r['profit_factor_forward']} "
            f"pf_historical={r['profit_factor_historical']} "
            f"verdict={r['verdict']}"
        )

    if not scorecard_ok:
        print("VERDICT=RS_BOTTOM_FORWARD_HEALTHCHECK_SCORECARD_FAILED")
        print("TEST_RS_BOTTOM_FORWARD_HEALTHCHECK_V1_OK")
        return 1

    print("VERDICT=RS_BOTTOM_FORWARD_HEALTHCHECK_READY")
    print("TEST_RS_BOTTOM_FORWARD_HEALTHCHECK_V1_OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
