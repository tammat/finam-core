#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import sys
from decimal import Decimal

import psycopg2


TABLE = "analytics_futures_rs_bottom_paper_observation_v1"

EXCLUDED_SYMBOLS = (
    "NGM6@RTSX",
    "NGN6@RTSX",
    "NGQ6@RTSX",
)

EXCLUDED_FILTERS = (
    "COMPRESSION_RANGE",
)

EXCLUDED_HOURS_MSK = (
    12,
)


def dec(v):
    return Decimal(str(v or 0))


def real_pf(pos, neg):
    pos = dec(pos)
    neg = dec(neg)
    if neg == 0 and pos > 0:
        return Decimal("999")
    if neg == 0:
        return Decimal("0")
    return pos / abs(neg)


def verdict(pf, expectancy, completed):
    if completed < 20:
        return "CLEAN_SUBSET_INSUFFICIENT_DATA"
    if pf >= Decimal("1.3") and expectancy > 0:
        return "CLEAN_SUBSET_EDGE_CANDIDATE"
    if pf < Decimal("1"):
        return "CLEAN_SUBSET_REJECTED"
    return "CLEAN_SUBSET_WEAK_OR_MIXED"


def main() -> int:
    print("=== RS_BOTTOM_CLEAN_SUBSET_REPLAY_V1 ===")
    print("mode=research_only")
    print("db_update=0")
    print("runtime_changed=0")
    print("execution_changed=0")
    print("real_trading_enabled=0")
    print("telegram_send=0")

    dsn = os.getenv("DATABASE_URL")
    if not dsn:
        print("VERDICT=DATABASE_URL_NOT_SET")
        return 1

    with psycopg2.connect(dsn) as conn:
        with conn.cursor() as cur:
            cur.execute(
                f"""
                with clean as (
                    select *
                    from {TABLE}
                    where symbol <> all(%s)
                      and filter_name <> all(%s)
                      and extract(hour from source_ts at time zone 'Europe/Moscow')::int <> all(%s)
                )
                select
                    count(*)::int as signals,
                    count(*) filter (where status='WAITING')::int as waiting,
                    count(*) filter (where status='SUCCESS')::int as success,
                    count(*) filter (where status='FAILURE')::int as failure,
                    count(*) filter (where status in ('SUCCESS','FAILURE'))::int as completed,
                    sum(return_pct) filter (where status='SUCCESS') as positive_sum,
                    sum(return_pct) filter (where status='FAILURE') as negative_sum,
                    avg(return_pct) filter (where status in ('SUCCESS','FAILURE')) as expectancy
                from clean
                """,
                (list(EXCLUDED_SYMBOLS), list(EXCLUDED_FILTERS), list(EXCLUDED_HOURS_MSK)),
            )

            (
                signals,
                waiting,
                success,
                failure,
                completed,
                positive_sum,
                negative_sum,
                expectancy,
            ) = cur.fetchone()

            signals = signals or 0
            waiting = waiting or 0
            success = success or 0
            failure = failure or 0
            completed = completed or 0
            positive_sum = dec(positive_sum)
            negative_sum = dec(negative_sum)
            expectancy = dec(expectancy)
            pf = real_pf(positive_sum, negative_sum)

            winrate = Decimal(success) / Decimal(completed) if completed else Decimal("0")
            v = verdict(pf, expectancy, completed)

            print(
                "CLEAN_SUBSET_ROW "
                f"signals={signals} "
                f"waiting={waiting} "
                f"success={success} "
                f"failure={failure} "
                f"completed={completed} "
                f"winrate={winrate:.6f} "
                f"positive_sum={positive_sum} "
                f"negative_sum={negative_sum} "
                f"expectancy={expectancy} "
                f"real_pf={pf:.6f} "
                f"verdict={v}"
            )

            cur.execute(
                f"""
                with clean as (
                    select *
                    from {TABLE}
                    where symbol <> all(%s)
                      and filter_name <> all(%s)
                      and extract(hour from source_ts at time zone 'Europe/Moscow')::int <> all(%s)
                )
                select
                    symbol,
                    count(*)::int as signals,
                    count(*) filter (where status='SUCCESS')::int as success,
                    count(*) filter (where status='FAILURE')::int as failure,
                    count(*) filter (where status in ('SUCCESS','FAILURE'))::int as completed,
                    sum(return_pct) filter (where status='SUCCESS') as positive_sum,
                    sum(return_pct) filter (where status='FAILURE') as negative_sum,
                    avg(return_pct) filter (where status in ('SUCCESS','FAILURE')) as expectancy
                from clean
                group by symbol
                order by completed desc, symbol
                """,
                (list(EXCLUDED_SYMBOLS), list(EXCLUDED_FILTERS), list(EXCLUDED_HOURS_MSK)),
            )

            for row in cur.fetchall():
                symbol, s, suc, fail, comp, pos, neg, exp = row
                pf_symbol = real_pf(pos, neg)
                print(
                    "CLEAN_SYMBOL_ROW "
                    f"symbol={symbol} "
                    f"signals={s} "
                    f"success={suc or 0} "
                    f"failure={fail or 0} "
                    f"completed={comp or 0} "
                    f"expectancy={dec(exp)} "
                    f"real_pf={pf_symbol:.6f}"
                )

    print("VERDICT=RS_BOTTOM_CLEAN_SUBSET_REPLAY_READY")
    print("TEST_RS_BOTTOM_CLEAN_SUBSET_REPLAY_V1_OK")
    return 0


if __name__ == "__main__":
    sys.exit(main())
