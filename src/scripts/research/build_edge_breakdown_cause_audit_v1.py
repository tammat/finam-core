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


def main() -> int:
    dsn = os.environ.get("DATABASE_URL")
    if not dsn:
        print("DATABASE_URL_NOT_SET")
        return 2

    print("=== EDGE_BREAKDOWN_CAUSE_AUDIT_V1 ===")
    print("mode=read_only")
    print("db_update=0")
    print("runtime_changed=0")
    print("execution_changed=0")
    print("real_trading_enabled=0")
    print(f"source_table={SOURCE_TABLE}")
    print(f"symbols={','.join(SYMBOLS)}")

    sql = """
    with base as (
        select
            symbol,
            signal_ts,
            created_at,
            status,
            return_pct,
            extract(hour from signal_ts at time zone 'Europe/Moscow')::int as hour_msk,
            signal_ts at time zone 'Europe/Moscow' as signal_msk
        from analytics_rs_bottom_runtime_dry_run_v1
        where symbol = any(%s)
          and status in ('SUCCESS','FAILURE')
          and return_pct is not null
    ),
    by_hour as (
        select
            symbol,
            hour_msk,
            count(*)::int as trades,
            count(*) filter (where return_pct > 0)::int as wins,
            count(*) filter (where return_pct <= 0)::int as losses,
            avg(return_pct) as avg_return,
            sum(return_pct) as total_return
        from base
        group by symbol, hour_msk
    ),
    worst_hour as (
        select distinct on (symbol)
            symbol,
            hour_msk,
            trades,
            wins,
            losses,
            avg_return,
            total_return
        from by_hour
        order by symbol, total_return asc
    ),
    evening as (
        select
            symbol,
            count(*) filter (where hour_msk >= 19)::int as evening_trades,
            avg(return_pct) filter (where hour_msk >= 19) as evening_avg,
            sum(return_pct) filter (where hour_msk >= 19) as evening_total,
            count(*) filter (where hour_msk < 19)::int as day_trades,
            avg(return_pct) filter (where hour_msk < 19) as day_avg,
            sum(return_pct) filter (where hour_msk < 19) as day_total
        from base
        group by symbol
    ),
    streak_src as (
        select
            *,
            case when return_pct <= 0 then 1 else 0 end as is_loss,
            row_number() over (partition by symbol order by signal_ts) as rn,
            row_number() over (
                partition by symbol, case when return_pct <= 0 then 1 else 0 end
                order by signal_ts
            ) as rn2
        from base
    ),
    loss_streaks as (
        select
            symbol,
            min(signal_ts) as streak_start_ts,
            max(signal_ts) as streak_end_ts,
            count(*)::int as streak_len,
            sum(return_pct) as streak_total
        from streak_src
        where is_loss = 1
        group by symbol, rn - rn2
    ),
    worst_streak as (
        select distinct on (symbol)
            symbol,
            streak_start_ts,
            streak_end_ts,
            streak_len,
            streak_total
        from loss_streaks
        order by symbol, streak_total asc
    ),
    final_stats as (
        select
            symbol,
            count(*)::int as completed,
            avg(return_pct) as avg_return,
            sum(return_pct) as total_return,
            count(*) filter (where return_pct > 0)::int as wins,
            count(*) filter (where return_pct <= 0)::int as losses,
            max(signal_ts) as last_signal_ts,
            max(created_at) as last_created_at
        from base
        group by symbol
    )
    select
        f.symbol,
        f.completed,
        f.wins,
        f.losses,
        f.avg_return,
        f.total_return,
        f.last_signal_ts,
        f.last_created_at,
        e.day_trades,
        e.day_avg,
        e.day_total,
        e.evening_trades,
        e.evening_avg,
        e.evening_total,
        wh.hour_msk as worst_hour_msk,
        wh.trades as worst_hour_trades,
        wh.wins as worst_hour_wins,
        wh.losses as worst_hour_losses,
        wh.avg_return as worst_hour_avg,
        wh.total_return as worst_hour_total,
        ws.streak_start_ts,
        ws.streak_end_ts,
        ws.streak_len,
        ws.streak_total
    from final_stats f
    left join evening e using(symbol)
    left join worst_hour wh using(symbol)
    left join worst_streak ws using(symbol)
    order by f.symbol
    """

    with psycopg.connect(dsn, row_factory=dict_row) as conn:
        with conn.cursor() as cur:
            cur.execute(sql, (list(SYMBOLS),))
            rows = cur.fetchall()

    print("\nCAUSE_ROWS")
    for r in rows:
        evening_total = float(r.get("evening_total") or 0)
        day_total = float(r.get("day_total") or 0)
        streak_total = float(r.get("streak_total") or 0)
        worst_hour = r.get("worst_hour_msk")

        if evening_total < 0 and evening_total < day_total:
            cause = "EVENING_SESSION_DEGRADATION"
        elif streak_total < -2:
            cause = "LOSS_STREAK_DOMINATES"
        elif worst_hour is not None and int(worst_hour) >= 19:
            cause = "LATE_SESSION_WORST_HOUR"
        else:
            cause = "NO_SINGLE_CAUSE_CONFIRMED"

        print(
            "CAUSE_ROW "
            f"symbol={r['symbol']} "
            f"completed={r['completed']} "
            f"wins={r['wins']} "
            f"losses={r['losses']} "
            f"avg_return={fmt(r['avg_return'])} "
            f"total_return={fmt(r['total_return'])} "
            f"day_trades={r['day_trades']} "
            f"day_avg={fmt(r['day_avg'])} "
            f"day_total={fmt(r['day_total'])} "
            f"evening_trades={r['evening_trades']} "
            f"evening_avg={fmt(r['evening_avg'])} "
            f"evening_total={fmt(r['evening_total'])} "
            f"worst_hour_msk={r['worst_hour_msk']} "
            f"worst_hour_trades={r['worst_hour_trades']} "
            f"worst_hour_total={fmt(r['worst_hour_total'])} "
            f"loss_streak_start={r['streak_start_ts']} "
            f"loss_streak_end={r['streak_end_ts']} "
            f"loss_streak_len={r['streak_len']} "
            f"loss_streak_total={fmt(r['streak_total'])} "
            f"probable_cause={cause}"
        )

    print("\nCAUSE_VERDICT")
    print("VERDICT=EDGE_BREAKDOWN_CAUSE_AUDIT_READY")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
