#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import sys
from decimal import Decimal

import psycopg2


TABLE = "analytics_futures_rs_bottom_paper_observation_v1"


def dec(v):
    return Decimal(str(v or 0))


def pf_real(pos, neg):
    pos = dec(pos)
    neg = dec(neg)
    if neg == 0 and pos > 0:
        return Decimal("999")
    if neg == 0:
        return Decimal("0")
    return pos / abs(neg)


def print_header():
    print("=== RS_BOTTOM_FAILURE_DECOMPOSITION_V1 ===")
    print("mode=read_only")
    print("db_update=0")
    print("runtime_changed=0")
    print("execution_changed=0")
    print("telegram_send=0")


def emit_group_rows(cur, *, title, row_prefix, group_expr, order_expr):
    print(f"=== {title} ===")

    cur.execute(
        f"""
        select
            {group_expr} as group_key,
            count(*)::int as signals,
            count(*) filter (where status='WAITING')::int as waiting,
            count(*) filter (where status='SUCCESS')::int as success,
            count(*) filter (where status='FAILURE')::int as failure,
            count(*) filter (where status in ('SUCCESS','FAILURE'))::int as completed,
            sum(return_pct) filter (where status='SUCCESS') as positive_sum,
            sum(return_pct) filter (where status='FAILURE') as negative_sum,
            avg(return_pct) filter (where status in ('SUCCESS','FAILURE')) as expectancy
        from {TABLE}
        group by group_key
        order by {order_expr}
        """
    )

    for row in cur.fetchall():
        (
            group_key,
            signals,
            waiting,
            success,
            failure,
            completed,
            positive_sum,
            negative_sum,
            expectancy,
        ) = row

        real_pf = pf_real(positive_sum, negative_sum)

        print(
            f"{row_prefix} "
            f"group={group_key} "
            f"signals={signals} "
            f"waiting={waiting} "
            f"success={success} "
            f"failure={failure} "
            f"completed={completed} "
            f"positive_sum={dec(positive_sum)} "
            f"negative_sum={dec(negative_sum)} "
            f"expectancy={dec(expectancy)} "
            f"real_pf={real_pf:.6f}"
        )


def main() -> int:
    print_header()

    dsn = os.getenv("DATABASE_URL")
    if not dsn:
        print("VERDICT=DATABASE_URL_NOT_SET")
        return 1

    with psycopg2.connect(dsn) as conn:
        with conn.cursor() as cur:
            emit_group_rows(
                cur,
                title="BY_FILTER",
                row_prefix="FILTER_ROW",
                group_expr="filter_name",
                order_expr="completed desc, group_key",
            )

            emit_group_rows(
                cur,
                title="BY_SELECTION_FILTER",
                row_prefix="SELECTION_FILTER_ROW",
                group_expr="selection || '/' || filter_name",
                order_expr="completed desc, group_key",
            )

            emit_group_rows(
                cur,
                title="BY_CONTRACT",
                row_prefix="CONTRACT_ROW",
                group_expr="symbol",
                order_expr="completed desc, group_key",
            )

            emit_group_rows(
                cur,
                title="BY_HOUR_MSK",
                row_prefix="HOUR_ROW",
                group_expr="extract(hour from source_ts at time zone 'Europe/Moscow')::int",
                order_expr="group_key",
            )

            print("=== WORST_OBSERVATIONS ===")
            cur.execute(
                f"""
                select
                    symbol,
                    selection,
                    filter_name,
                    source_ts,
                    source_close,
                    future_ts,
                    future_close,
                    return_pct,
                    status
                from {TABLE}
                where status='FAILURE'
                order by return_pct asc nulls last
                limit 20
                """
            )

            for row in cur.fetchall():
                (
                    symbol,
                    selection,
                    filter_name,
                    source_ts,
                    source_close,
                    future_ts,
                    future_close,
                    return_pct,
                    status,
                ) = row

                print(
                    "WORST_ROW "
                    f"symbol={symbol} "
                    f"selection={selection} "
                    f"filter={filter_name} "
                    f"source_ts={source_ts} "
                    f"source_close={source_close} "
                    f"future_ts={future_ts} "
                    f"future_close={future_close} "
                    f"return_pct={return_pct} "
                    f"status={status}"
                )

            print("=== BEST_OBSERVATIONS ===")
            cur.execute(
                f"""
                select
                    symbol,
                    selection,
                    filter_name,
                    source_ts,
                    source_close,
                    future_ts,
                    future_close,
                    return_pct,
                    status
                from {TABLE}
                where status='SUCCESS'
                order by return_pct desc nulls last
                limit 20
                """
            )

            for row in cur.fetchall():
                (
                    symbol,
                    selection,
                    filter_name,
                    source_ts,
                    source_close,
                    future_ts,
                    future_close,
                    return_pct,
                    status,
                ) = row

                print(
                    "BEST_ROW "
                    f"symbol={symbol} "
                    f"selection={selection} "
                    f"filter={filter_name} "
                    f"source_ts={source_ts} "
                    f"source_close={source_close} "
                    f"future_ts={future_ts} "
                    f"future_close={future_close} "
                    f"return_pct={return_pct} "
                    f"status={status}"
                )

    print("VERDICT=RS_BOTTOM_FAILURE_DECOMPOSITION_READY")
    print("TEST_RS_BOTTOM_FAILURE_DECOMPOSITION_V1_OK")
    return 0


if __name__ == "__main__":
    sys.exit(main())
