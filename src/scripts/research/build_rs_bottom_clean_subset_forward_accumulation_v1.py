#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import sys
from decimal import Decimal

import psycopg2


TABLE = "analytics_futures_rs_bottom_paper_observation_v1"
TARGET_COMPLETED = 100

EXCLUDED_SYMBOLS = ["NGM6@RTSX", "NGN6@RTSX", "NGQ6@RTSX"]
EXCLUDED_FILTERS = ["COMPRESSION_RANGE"]
EXCLUDED_HOURS_MSK = [12]


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


def main() -> int:
    print("=== RS_BOTTOM_CLEAN_SUBSET_FORWARD_ACCUMULATION_V1 ===")
    print("mode=read_only_accumulation")
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
                    avg(return_pct) filter (where status in ('SUCCESS','FAILURE')) as expectancy,
                    max(source_ts) as last_signal_ts
                from clean
                """,
                (EXCLUDED_SYMBOLS, EXCLUDED_FILTERS, EXCLUDED_HOURS_MSK),
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
                last_signal_ts,
            ) = cur.fetchone()

            signals = signals or 0
            waiting = waiting or 0
            success = success or 0
            failure = failure or 0
            completed = completed or 0
            pf = real_pf(positive_sum, negative_sum)
            expectancy = dec(expectancy)
            winrate = Decimal(success) / Decimal(completed) if completed else Decimal("0")
            remaining = max(TARGET_COMPLETED - completed, 0)

            if completed >= TARGET_COMPLETED and pf >= Decimal("1.3") and expectancy > 0:
                decision = "READY_FOR_REVIEW_NOT_LIVE"
            elif completed >= TARGET_COMPLETED:
                decision = "TARGET_REACHED_BUT_EDGE_WEAK_REVIEW"
            else:
                decision = "ACCUMULATION_CONTINUE"

            print(
                "ACCUMULATION_ROW "
                f"target_completed={TARGET_COMPLETED} "
                f"signals={signals} "
                f"waiting={waiting} "
                f"completed={completed} "
                f"remaining={remaining} "
                f"success={success} "
                f"failure={failure} "
                f"winrate={winrate:.6f} "
                f"real_pf={pf:.6f} "
                f"expectancy={expectancy} "
                f"last_signal_ts={last_signal_ts} "
                f"decision={decision}"
            )

    print("VERDICT=RS_BOTTOM_CLEAN_SUBSET_FORWARD_ACCUMULATION_READY")
    print("TEST_RS_BOTTOM_CLEAN_SUBSET_FORWARD_ACCUMULATION_V1_OK")
    return 0


if __name__ == "__main__":
    sys.exit(main())
