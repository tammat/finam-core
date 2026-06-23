#!/usr/bin/env python3
from __future__ import annotations

import os
from decimal import Decimal
import psycopg
from psycopg.rows import dict_row

TABLE = "analytics_futures_rs_bottom_paper_observation_v1"

ALLOWED_SYMBOLS = (
    "GLU6@RTSX",
    "GDU6@RTSX",
    "BRN6@RTSX",
    "NGM6@RTSX",
    "USDRUBF@RTSX",
)

EXCLUDED_HOURS_MSK = (12, 13, 14)
SELECTION = "BOTTOM3"
FILTER_NAME = "COMPRESSION_RANGE"


def dec(v) -> Decimal:
    return Decimal(str(v or 0))


def print_rows(title: str, rows: list[dict]) -> None:
    print(f"\n=== {title} ===")
    for r in rows:
        print(
            "ROW "
            + " ".join(f"{k}={v}" for k, v in r.items())
        )


def main() -> int:
    db_url = os.environ.get("DATABASE_URL")
    if not db_url:
        print("ERROR=DATABASE_URL_NOT_SET")
        return 2

    print("=== RS_BOTTOM_SESSION_FILTER_WALKFORWARD_V1 ===")
    print("mode=read_only")
    print("db_update=0")
    print("runtime_changed=0")
    print("execution_changed=0")
    print("real_trading_enabled=0")
    print(f"selection={SELECTION}")
    print(f"filter_name={FILTER_NAME}")
    print("allowed_symbols=" + ",".join(ALLOWED_SYMBOLS))
    print("excluded_hours_msk=" + ",".join(map(str, EXCLUDED_HOURS_MSK)))

    with psycopg.connect(db_url, row_factory=dict_row) as conn:
        with conn.cursor() as cur:
            base_where = f"""
                from {TABLE}
                where selection = %s
                  and filter_name = %s
                  and symbol = any(%s)
                  and extract(hour from source_ts at time zone 'Europe/Moscow')::int <> all(%s)
                  and status in ('SUCCESS', 'FAILURE')
                  and return_pct is not null
            """
            params = (SELECTION, FILTER_NAME, list(ALLOWED_SYMBOLS), list(EXCLUDED_HOURS_MSK))

            cur.execute(
                f"""
                select
                    source_ts::date as trade_day,
                    count(*)::int as completed,
                    count(*) filter (where status='SUCCESS')::int as success,
                    count(*) filter (where status='FAILURE')::int as failure,
                    avg(return_pct) as expectancy,
                    case
                        when abs(sum(least(return_pct, 0))) > 0
                        then sum(greatest(return_pct, 0)) / abs(sum(least(return_pct, 0)))
                        else null
                    end as profit_factor,
                    avg(case when status='SUCCESS' then 1.0 else 0.0 end) as winrate
                {base_where}
                group by source_ts::date
                order by trade_day;
                """,
                params,
            )
            by_day = cur.fetchall()

            cur.execute(
                f"""
                select
                    symbol,
                    count(*)::int as completed,
                    count(*) filter (where status='SUCCESS')::int as success,
                    count(*) filter (where status='FAILURE')::int as failure,
                    avg(return_pct) as expectancy,
                    case
                        when abs(sum(least(return_pct, 0))) > 0
                        then sum(greatest(return_pct, 0)) / abs(sum(least(return_pct, 0)))
                        else null
                    end as profit_factor,
                    avg(case when status='SUCCESS' then 1.0 else 0.0 end) as winrate
                {base_where}
                group by symbol
                order by profit_factor desc nulls last, completed desc;
                """,
                params,
            )
            by_symbol = cur.fetchall()

            cur.execute(
                f"""
                select
                    extract(hour from source_ts at time zone 'Europe/Moscow')::int as hour_msk,
                    count(*)::int as completed,
                    count(*) filter (where status='SUCCESS')::int as success,
                    count(*) filter (where status='FAILURE')::int as failure,
                    avg(return_pct) as expectancy,
                    case
                        when abs(sum(least(return_pct, 0))) > 0
                        then sum(greatest(return_pct, 0)) / abs(sum(least(return_pct, 0)))
                        else null
                    end as profit_factor,
                    avg(case when status='SUCCESS' then 1.0 else 0.0 end) as winrate
                {base_where}
                group by extract(hour from source_ts at time zone 'Europe/Moscow')::int
                order by hour_msk;
                """,
                params,
            )
            by_hour = cur.fetchall()

            cur.execute(
                f"""
                with src as (
                    select
                        source_ts,
                        symbol,
                        return_pct,
                        sum(return_pct) over (
                            order by source_ts, symbol
                            rows between unbounded preceding and current row
                        ) as equity
                    {base_where}
                ),
                dd as (
                    select
                        source_ts,
                        symbol,
                        return_pct,
                        equity,
                        max(equity) over (
                            order by source_ts, symbol
                            rows between unbounded preceding and current row
                        ) as peak
                    from src
                )
                select
                    count(*)::int as curve_points,
                    min(equity - peak) as max_drawdown,
                    max(equity) as max_equity,
                    min(equity) as min_equity,
                    sum(return_pct) as total_return
                from dd;
                """,
                params,
            )
            curve = cur.fetchone() or {}

    print_rows("WALKFORWARD_BY_DAY", by_day)
    print_rows("WALKFORWARD_BY_SYMBOL", by_symbol)
    print_rows("WALKFORWARD_BY_HOUR_MSK", by_hour)

    positive_days = sum(1 for r in by_day if dec(r["expectancy"]) > 0 and dec(r["profit_factor"]) > 1)
    weak_days = sum(1 for r in by_day if dec(r["expectancy"]) <= 0 or dec(r["profit_factor"]) <= 1)

    positive_symbols = sum(1 for r in by_symbol if dec(r["expectancy"]) > 0 and dec(r["profit_factor"]) >= Decimal("1.3"))
    completed_total = sum(int(r["completed"] or 0) for r in by_day)

    pf_values = [dec(r["profit_factor"]) for r in by_day if r["profit_factor"] is not None]
    min_day_pf = min(pf_values) if pf_values else Decimal("0")
    min_day_completed = min((int(r["completed"] or 0) for r in by_day), default=0)

    print("\nEQUITY_CURVE_SUMMARY")
    print(
        "curve_points={curve_points} total_return={total_return} "
        "max_equity={max_equity} min_equity={min_equity} max_drawdown={max_drawdown}".format(**curve)
    )

    print("\nWALKFORWARD_SUMMARY")
    print(f"days_total={len(by_day)}")
    print(f"positive_days={positive_days}")
    print(f"weak_days={weak_days}")
    print(f"positive_symbols={positive_symbols}")
    print(f"completed_total={completed_total}")
    print(f"min_day_pf={min_day_pf}")
    print(f"min_day_completed={min_day_completed}")

    confirmed = (
        len(by_day) >= 2
        and positive_days == len(by_day)
        and positive_symbols >= 3
        and completed_total >= 100
        and min_day_pf >= Decimal("1.3")
        and dec(curve.get("max_drawdown")) >= Decimal("-10")
    )

    if confirmed:
        verdict = "RS_BOTTOM_SESSION_FILTER_WALKFORWARD_CONFIRMED"
    elif positive_days >= 1 and positive_symbols >= 2:
        verdict = "RS_BOTTOM_SESSION_FILTER_WALKFORWARD_PROMISING_BUT_WEAK"
    else:
        verdict = "RS_BOTTOM_SESSION_FILTER_WALKFORWARD_REJECT"

    print("VERDICT=" + verdict)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
