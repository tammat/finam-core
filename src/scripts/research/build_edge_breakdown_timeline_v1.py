#!/usr/bin/env python3
from __future__ import annotations

import os
from typing import Any

import psycopg
from psycopg.rows import dict_row

SYMBOLS = ("GDU6@RTSX", "GLU6@RTSX", "NGM6@RTSX")
SOURCE_TABLE = "analytics_rs_bottom_runtime_dry_run_v1"


def fmt(x: Any, n: int = 4) -> str:
    if x is None:
        return "NONE"
    try:
        return f"{float(x):.{n}f}"
    except Exception:
        return str(x)


def classify(pf: Any, avg_return: Any, completed: int) -> str:
    pfv = float(pf or 0)
    avgv = float(avg_return or 0)
    if completed >= 20 and pfv >= 1.5 and avgv > 0:
        return "OK"
    if completed >= 10 and pfv >= 1.0 and avgv > 0:
        return "WATCH"
    return "BROKEN"


def main() -> int:
    dsn = os.environ.get("DATABASE_URL")
    if not dsn:
        print("DATABASE_URL_NOT_SET")
        return 2

    print("=== EDGE_BREAKDOWN_TIMELINE_V1 ===")
    print("mode=read_only")
    print("db_update=0")
    print("runtime_changed=0")
    print("execution_changed=0")
    print("real_trading_enabled=0")
    print(f"source_table={SOURCE_TABLE}")
    print(f"symbols={','.join(SYMBOLS)}")

    summary_sql = """
    with base as (
        select
            symbol,
            signal_ts,
            created_at,
            status,
            return_pct,
            extract(hour from signal_ts at time zone 'Europe/Moscow')::int as hour_msk
        from analytics_rs_bottom_runtime_dry_run_v1
        where symbol = any(%s)
          and status in ('SUCCESS','FAILURE')
          and return_pct is not null
    ),
    ordered as (
        select
            *,
            row_number() over (partition by symbol order by signal_ts) as rn,
            sum(return_pct) over (
                partition by symbol order by signal_ts
                rows between unbounded preceding and current row
            ) as cum_return,
            avg(return_pct) over (
                partition by symbol order by signal_ts
                rows between unbounded preceding and current row
            ) as rolling_avg,
            sum(greatest(return_pct, 0)) over (
                partition by symbol order by signal_ts
                rows between unbounded preceding and current row
            ) as rolling_pos,
            abs(sum(least(return_pct, 0)) over (
                partition by symbol order by signal_ts
                rows between unbounded preceding and current row
            )) as rolling_neg
        from base
    ),
    timeline as (
        select
            *,
            case when rolling_neg > 0 then rolling_pos / rolling_neg else null end as rolling_pf
        from ordered
    ),
    breakdown as (
        select
            symbol,
            min(signal_ts) filter (where rolling_avg < 0) as first_negative_avg_ts,
            min(signal_ts) filter (where rolling_pf < 1) as first_pf_below_1_ts,
            min(signal_ts) filter (where cum_return < 0) as first_cum_negative_ts
        from timeline
        group by symbol
    ),
    final_stats as (
        select
            symbol,
            count(*)::int as completed,
            count(*) filter (where return_pct > 0)::int as success,
            count(*) filter (where return_pct <= 0)::int as failure,
            avg(return_pct) as avg_return,
            sum(return_pct) as total_return,
            case
                when abs(sum(least(return_pct, 0))) > 0
                then sum(greatest(return_pct, 0)) / abs(sum(least(return_pct, 0)))
                else null
            end as profit_factor,
            min(signal_ts) as first_signal_ts,
            max(signal_ts) as last_signal_ts,
            max(created_at) as last_created_at
        from base
        group by symbol
    ),
    hour_stats as (
        select
            symbol,
            hour_msk,
            count(*)::int as completed,
            avg(return_pct) as avg_return,
            sum(return_pct) as total_return
        from base
        group by symbol, hour_msk
    ),
    worst_hours as (
        select distinct on (symbol)
            symbol,
            hour_msk as worst_hour_msk,
            completed as worst_hour_completed,
            avg_return as worst_hour_avg,
            total_return as worst_hour_total
        from hour_stats
        order by symbol, total_return asc
    )
    select
        fs.*,
        bd.first_negative_avg_ts,
        bd.first_pf_below_1_ts,
        bd.first_cum_negative_ts,
        wh.worst_hour_msk,
        wh.worst_hour_completed,
        wh.worst_hour_avg,
        wh.worst_hour_total
    from final_stats fs
    left join breakdown bd using(symbol)
    left join worst_hours wh using(symbol)
    order by symbol
    """

    timeline_sql = """
    with base as (
        select
            symbol,
            signal_ts,
            signal_ts at time zone 'Europe/Moscow' as signal_msk,
            status,
            return_pct
        from analytics_rs_bottom_runtime_dry_run_v1
        where symbol = any(%s)
          and status in ('SUCCESS','FAILURE')
          and return_pct is not null
    ),
    t as (
        select
            symbol,
            signal_ts,
            signal_msk,
            status,
            return_pct,
            row_number() over (partition by symbol order by signal_ts) as rn,
            sum(return_pct) over (
                partition by symbol order by signal_ts
                rows between unbounded preceding and current row
            ) as cum_return,
            avg(return_pct) over (
                partition by symbol order by signal_ts
                rows between unbounded preceding and current row
            ) as rolling_avg
        from base
    )
    select *
    from t
    where rn <= 5
       or rolling_avg < 0
       or rn >= (select max(rn) - 5 from t t2 where t2.symbol = t.symbol)
    order by symbol, signal_ts
    """

    with psycopg.connect(dsn, row_factory=dict_row) as conn:
        with conn.cursor() as cur:
            cur.execute(summary_sql, (list(SYMBOLS),))
            rows = cur.fetchall()

            print("\nBREAKDOWN_SUMMARY")
            broken = 0
            for r in rows:
                verdict = classify(r.get("profit_factor"), r.get("avg_return"), int(r.get("completed") or 0))
                if verdict == "BROKEN":
                    broken += 1

                print(
                    "BREAKDOWN_ROW "
                    f"symbol={r['symbol']} "
                    f"completed={r['completed']} "
                    f"success={r['success']} "
                    f"failure={r['failure']} "
                    f"avg_return={fmt(r['avg_return'])} "
                    f"total_return={fmt(r['total_return'])} "
                    f"profit_factor={fmt(r['profit_factor'])} "
                    f"first_signal_ts={r['first_signal_ts']} "
                    f"last_signal_ts={r['last_signal_ts']} "
                    f"first_negative_avg_ts={r['first_negative_avg_ts']} "
                    f"first_pf_below_1_ts={r['first_pf_below_1_ts']} "
                    f"first_cum_negative_ts={r['first_cum_negative_ts']} "
                    f"worst_hour_msk={r['worst_hour_msk']} "
                    f"worst_hour_completed={r['worst_hour_completed']} "
                    f"worst_hour_avg={fmt(r['worst_hour_avg'])} "
                    f"worst_hour_total={fmt(r['worst_hour_total'])} "
                    f"verdict={verdict}"
                )

            cur.execute(timeline_sql, (list(SYMBOLS),))
            trows = cur.fetchall()

            print("\nTIMELINE_ROWS")
            for r in trows:
                print(
                    "TIMELINE_ROW "
                    f"symbol={r['symbol']} "
                    f"rn={r['rn']} "
                    f"signal_ts={r['signal_ts']} "
                    f"signal_msk={r['signal_msk']} "
                    f"status={r['status']} "
                    f"return_pct={fmt(r['return_pct'])} "
                    f"cum_return={fmt(r['cum_return'])} "
                    f"rolling_avg={fmt(r['rolling_avg'])}"
                )

    print("\nBREAKDOWN_VERDICT")
    if broken > 0:
        print("VERDICT=EDGE_BREAKDOWN_DETECTED")
    else:
        print("VERDICT=EDGE_BREAKDOWN_NOT_DETECTED")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
