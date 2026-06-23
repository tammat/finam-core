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


def d(x) -> Decimal:
    if x is None:
        return Decimal("0")
    return Decimal(str(x))


def main() -> int:
    db_url = os.environ.get("DATABASE_URL")
    if not db_url:
        print("ERROR=DATABASE_URL_NOT_SET")
        return 2

    print("=== RS_BOTTOM_SESSION_FILTER_REPLAY_V1 ===")
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
            cur.execute(
                f"""
                with src as (
                    select
                        symbol,
                        selection,
                        filter_name,
                        source_ts,
                        future_ts,
                        source_close,
                        future_close,
                        return_pct,
                        status,
                        extract(hour from source_ts at time zone 'Europe/Moscow')::int as hour_msk
                    from {TABLE}
                    where selection = %s
                      and filter_name = %s
                      and symbol = any(%s)
                      and extract(hour from source_ts at time zone 'Europe/Moscow')::int <> all(%s)
                      and status in ('SUCCESS', 'FAILURE')
                      and return_pct is not null
                ),
                agg as (
                    select
                        count(*)::int as completed,
                        count(*) filter (where status = 'SUCCESS')::int as success,
                        count(*) filter (where status = 'FAILURE')::int as failure,
                        avg(return_pct) as expectancy,
                        sum(greatest(return_pct, 0)) as positive_sum,
                        abs(sum(least(return_pct, 0))) as negative_sum,
                        case
                            when abs(sum(least(return_pct, 0))) > 0
                            then sum(greatest(return_pct, 0)) / abs(sum(least(return_pct, 0)))
                            else null
                        end as profit_factor,
                        avg(case when status = 'SUCCESS' then 1.0 else 0.0 end) as winrate,
                        min(source_ts) as first_ts,
                        max(source_ts) as last_ts
                    from src
                )
                select * from agg;
                """,
                (SELECTION, FILTER_NAME, list(ALLOWED_SYMBOLS), list(EXCLUDED_HOURS_MSK)),
            )
            summary = cur.fetchone() or {}

            cur.execute(
                f"""
                with src as (
                    select
                        symbol,
                        return_pct,
                        status,
                        source_ts,
                        extract(hour from source_ts at time zone 'Europe/Moscow')::int as hour_msk
                    from {TABLE}
                    where selection = %s
                      and filter_name = %s
                      and symbol = any(%s)
                      and extract(hour from source_ts at time zone 'Europe/Moscow')::int <> all(%s)
                      and status in ('SUCCESS', 'FAILURE')
                      and return_pct is not null
                )
                select
                    symbol,
                    count(*)::int as completed,
                    count(*) filter (where status = 'SUCCESS')::int as success,
                    count(*) filter (where status = 'FAILURE')::int as failure,
                    avg(return_pct) as expectancy,
                    case
                        when abs(sum(least(return_pct, 0))) > 0
                        then sum(greatest(return_pct, 0)) / abs(sum(least(return_pct, 0)))
                        else null
                    end as profit_factor
                from src
                group by symbol
                order by profit_factor desc nulls last, completed desc;
                """,
                (SELECTION, FILTER_NAME, list(ALLOWED_SYMBOLS), list(EXCLUDED_HOURS_MSK)),
            )
            by_symbol = cur.fetchall()

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
                    from {TABLE}
                    where selection = %s
                      and filter_name = %s
                      and symbol = any(%s)
                      and extract(hour from source_ts at time zone 'Europe/Moscow')::int <> all(%s)
                      and status in ('SUCCESS', 'FAILURE')
                      and return_pct is not null
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
                    min(equity - peak) as max_drawdown,
                    max(equity) as max_equity,
                    min(equity) as min_equity,
                    count(*)::int as curve_points
                from dd;
                """,
                (SELECTION, FILTER_NAME, list(ALLOWED_SYMBOLS), list(EXCLUDED_HOURS_MSK)),
            )
            curve = cur.fetchone() or {}

    completed = int(summary.get("completed") or 0)
    expectancy = d(summary.get("expectancy"))
    pf = summary.get("profit_factor")
    pf_d = d(pf) if pf is not None else Decimal("0")
    winrate = d(summary.get("winrate"))
    max_dd = d(curve.get("max_drawdown"))

    print("\nREPLAY_SUMMARY")
    print(
        "completed={completed} success={success} failure={failure} "
        "expectancy={expectancy} profit_factor={pf} winrate={winrate} "
        "first_ts={first_ts} last_ts={last_ts}".format(
            completed=completed,
            success=summary.get("success"),
            failure=summary.get("failure"),
            expectancy=summary.get("expectancy"),
            pf=summary.get("profit_factor"),
            winrate=summary.get("winrate"),
            first_ts=summary.get("first_ts"),
            last_ts=summary.get("last_ts"),
        )
    )

    print("\nREPLAY_SYMBOL_ROWS")
    for r in by_symbol:
        print(
            "SYMBOL_ROW symbol={symbol} completed={completed} success={success} "
            "failure={failure} expectancy={expectancy} profit_factor={profit_factor}".format(**r)
        )

    print("\nEQUITY_CURVE_SUMMARY")
    print(
        "curve_points={curve_points} max_equity={max_equity} "
        "min_equity={min_equity} max_drawdown={max_drawdown}".format(**curve)
    )

    positive_edge = completed >= 100 and expectancy > 0 and pf_d >= Decimal("1.3")
    drawdown_ok = max_dd >= Decimal("-50")

    if positive_edge and drawdown_ok:
        verdict = "RS_BOTTOM_SESSION_FILTER_REPLAY_CANDIDATE_CONFIRMED"
    elif positive_edge:
        verdict = "RS_BOTTOM_SESSION_FILTER_REPLAY_EDGE_WITH_DRAWDOWN_RISK"
    else:
        verdict = "RS_BOTTOM_SESSION_FILTER_REPLAY_REJECT"

    print(f"positive_edge={1 if positive_edge else 0}")
    print(f"drawdown_ok={1 if drawdown_ok else 0}")
    print("VERDICT=" + verdict)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
