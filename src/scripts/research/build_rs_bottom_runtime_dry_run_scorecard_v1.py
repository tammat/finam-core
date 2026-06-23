#!/usr/bin/env python3
from __future__ import annotations

import os
from decimal import Decimal

import psycopg
from psycopg.rows import dict_row

TABLE = "analytics_rs_bottom_runtime_dry_run_v1"
STRATEGY = "RS_BOTTOM_RUNTIME_DRY_RUN_V1"
SYMBOLS = ("GDU6@RTSX", "GLU6@RTSX", "NGM6@RTSX")


def main() -> int:
    dsn = os.environ.get("DATABASE_URL")
    if not dsn:
        print("ERROR=DATABASE_URL_NOT_SET")
        return 2

    print("=== RS_BOTTOM_RUNTIME_DRY_RUN_SCORECARD_V1 ===")
    print("mode=read_only")
    print("db_update=0")
    print("runtime_changed=0")
    print("execution_changed=0")
    print("real_trading_enabled=0")
    print("paper_orders=0")
    print(f"source_table={TABLE}")
    print(f"strategy={STRATEGY}")
    print("symbols=" + ",".join(SYMBOLS))

    sql = f"""
        with base as (
            select
                symbol,
                family,
                signal_ts,
                return_pct,
                status
            from {TABLE}
            where strategy = %s
              and symbol = any(%s)
              and horizon_min = 240
              and selection = 'BOTTOM3'
              and filter_name = 'COMPRESSION_RANGE'
        ),
        completed as (
            select *
            from base
            where status in ('SUCCESS', 'FAILURE')
              and return_pct is not null
        ),
        curve as (
            select
                symbol,
                signal_ts,
                sum(return_pct) over (
                    partition by symbol
                    order by signal_ts
                    rows between unbounded preceding and current row
                ) as equity
            from completed
        ),
        curve_with_peak as (
            select
                symbol,
                signal_ts,
                equity,
                max(equity) over (
                    partition by symbol
                    order by signal_ts
                    rows between unbounded preceding and current row
                ) as peak_equity
            from curve
        ),
        dd as (
            select
                symbol,
                min(equity - peak_equity) as max_drawdown
            from curve_with_peak
            group by symbol
        ),
        agg as (
            select
                b.symbol,
                coalesce(max(b.family), 'UNKNOWN') as family,
                count(*)::int as signals_total,
                count(*) filter (where b.status='SUCCESS')::int as success,
                count(*) filter (where b.status='FAILURE')::int as failure,
                count(*) filter (where b.status='WAITING')::int as waiting,
                count(*) filter (where b.status in ('SUCCESS','FAILURE'))::int as completed,
                avg(b.return_pct) filter (where b.status in ('SUCCESS','FAILURE')) as expectancy,
                case
                    when abs(sum(least(b.return_pct, 0)) filter (where b.status in ('SUCCESS','FAILURE'))) > 0
                    then
                        sum(greatest(b.return_pct, 0)) filter (where b.status in ('SUCCESS','FAILURE'))
                        / abs(sum(least(b.return_pct, 0)) filter (where b.status in ('SUCCESS','FAILURE')))
                    else null
                end as profit_factor,
                avg(case when b.status='SUCCESS' then 1.0 when b.status='FAILURE' then 0.0 else null end) as winrate,
                min(b.signal_ts) as first_ts,
                max(b.signal_ts) as last_ts
            from base b
            group by b.symbol
        )
        select
            agg.*,
            dd.max_drawdown
        from agg
        left join dd using (symbol)
        order by profit_factor desc nulls last, completed desc
    """

    with psycopg.connect(dsn, row_factory=dict_row) as conn:
        with conn.cursor() as cur:
            cur.execute(sql, (STRATEGY, list(SYMBOLS)))
            rows = cur.fetchall()

    print("\nSCORECARD_ROWS")

    confirmed = 0
    completed_total = 0

    for r in rows:
        completed = int(r["completed"] or 0)
        pf = Decimal(str(r["profit_factor"] or 0))
        expectancy = Decimal(str(r["expectancy"] or 0))
        max_dd = Decimal(str(r["max_drawdown"] or 0))

        if completed >= 15 and pf >= Decimal("1.5") and expectancy > 0:
            verdict = "CONFIRMED"
            confirmed += 1
        elif completed >= 15 and pf >= Decimal("1.0") and expectancy > 0:
            verdict = "WATCH"
        else:
            verdict = "REJECT"

        completed_total += completed

        print(
            f"SCORECARD_ROW symbol={r['symbol']} family={r['family']} "
            f"signals_total={r['signals_total']} completed={r['completed']} "
            f"success={r['success']} failure={r['failure']} waiting={r['waiting']} "
            f"expectancy={r['expectancy']} profit_factor={r['profit_factor']} "
            f"winrate={r['winrate']} max_drawdown={max_dd} "
            f"first_ts={r['first_ts']} last_ts={r['last_ts']} verdict={verdict}"
        )

    print("\nSCORECARD_SUMMARY")
    print(f"symbols_total={len(SYMBOLS)}")
    print(f"rows_returned={len(rows)}")
    print(f"confirmed_symbols={confirmed}")
    print(f"completed_total={completed_total}")
    print("db_update=0")
    print("runtime_changed=0")
    print("execution_changed=0")
    print("real_trading_enabled=0")
    print("paper_orders=0")

    if confirmed >= 2 and completed_total >= 50:
        print("VERDICT=RS_BOTTOM_RUNTIME_DRY_RUN_SCORECARD_CONFIRMED")
    else:
        print("VERDICT=RS_BOTTOM_RUNTIME_DRY_RUN_SCORECARD_NOT_CONFIRMED")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
