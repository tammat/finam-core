#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import sys
from decimal import Decimal

import psycopg2


WINDOWS = [
    ("7D", "7 day"),
    ("14D", "14 day"),
    ("30D", "30 day"),
    ("ALL", None),
]


def dec(v):
    return Decimal(str(v or 0))


def fmt(v):
    if v is None:
        return "0"
    return str(v)


def pf_real(positive_sum, negative_sum):
    pos = dec(positive_sum)
    neg = dec(negative_sum)

    if neg == 0 and pos > 0:
        return Decimal("999")
    if neg == 0:
        return Decimal("0")

    return pos / abs(neg)


def verdict_for(pf, expectancy, completed):
    if completed < 10:
        return "INSUFFICIENT_DATA"
    if pf >= Decimal("1.5") and expectancy > 0:
        return "EDGE_STABLE"
    if pf >= Decimal("1.0") and expectancy > 0:
        return "EDGE_WEAK_POSITIVE"
    if pf < Decimal("1.0"):
        return "EDGE_BROKEN"
    return "EDGE_MIXED"


def main() -> int:
    print("=== EDGE_STABILITY_REPORT_V1_1_REAL_PF ===")
    print("mode=read_only")
    print("db_update=0")
    print("runtime_changed=0")
    print("execution_changed=0")
    print("telegram_send=0")

    dsn = os.getenv("DATABASE_URL")
    if not dsn:
        print("VERDICT=DATABASE_URL_NOT_SET")
        return 1

    table = "analytics_futures_rs_bottom_paper_observation_v1"

    with psycopg2.connect(dsn) as conn:
        with conn.cursor() as cur:
            cur.execute(
                f"""
                select distinct selection, filter_name
                from {table}
                order by selection, filter_name
                """
            )
            candidates = cur.fetchall()

            for selection, filter_name in candidates:
                print(f"CANDIDATE selection={selection} filter={filter_name}")

                pf_by_window = {}

                for label, interval_expr in WINDOWS:
                    where_window = ""
                    if interval_expr:
                        where_window = f"and source_ts >= now() - interval '{interval_expr}'"

                    cur.execute(
                        f"""
                        select
                            count(*)::int as signals,
                            count(*) filter (where status='SUCCESS')::int as success,
                            count(*) filter (where status='FAILURE')::int as failure,
                            count(*) filter (where status in ('SUCCESS','FAILURE'))::int as completed,
                            avg(return_pct) filter (where status in ('SUCCESS','FAILURE')) as expectancy,
                            sum(return_pct) filter (where status='SUCCESS') as positive_sum,
                            sum(return_pct) filter (where status='FAILURE') as negative_sum,
                            avg(return_pct) filter (where status='SUCCESS') as avg_win,
                            avg(return_pct) filter (where status='FAILURE') as avg_loss
                        from {table}
                        where selection=%s
                          and filter_name=%s
                          {where_window}
                        """,
                        (selection, filter_name),
                    )

                    (
                        signals,
                        success,
                        failure,
                        completed,
                        expectancy,
                        positive_sum,
                        negative_sum,
                        avg_win,
                        avg_loss,
                    ) = cur.fetchone()

                    signals = signals or 0
                    success = success or 0
                    failure = failure or 0
                    completed = completed or 0
                    expectancy = dec(expectancy)
                    positive_sum = dec(positive_sum)
                    negative_sum = dec(negative_sum)
                    avg_win = dec(avg_win)
                    avg_loss = dec(avg_loss)

                    winrate = Decimal(success) / Decimal(completed) if completed else Decimal("0")
                    real_pf = pf_real(positive_sum, negative_sum)
                    verdict = verdict_for(real_pf, expectancy, completed)

                    pf_by_window[label] = real_pf

                    print(
                        f"WINDOW={label} "
                        f"signals={signals} "
                        f"completed={completed} "
                        f"success={success} "
                        f"failure={failure} "
                        f"winrate={winrate:.4f} "
                        f"positive_sum={positive_sum} "
                        f"negative_sum={negative_sum} "
                        f"avg_win={avg_win} "
                        f"avg_loss={avg_loss} "
                        f"expectancy={expectancy} "
                        f"real_pf={real_pf:.6f} "
                        f"verdict={verdict}"
                    )

                pf7 = pf_by_window.get("7D", Decimal("0"))
                pf14 = pf_by_window.get("14D", Decimal("0"))
                pf30 = pf_by_window.get("30D", Decimal("0"))

                if pf7 >= Decimal("1.5") and pf14 >= Decimal("1.5") and pf30 >= Decimal("1.5"):
                    stability = "EDGE_STABLE_REAL_PF"
                elif pf7 < Decimal("1.0") and pf14 < Decimal("1.0"):
                    stability = "EDGE_BROKEN_REAL_PF"
                elif pf7 < pf14 < pf30:
                    stability = "EDGE_DECAYING_REAL_PF"
                else:
                    stability = "EDGE_MIXED_REAL_PF"

                print(
                    f"EDGE_VERDICT selection={selection} "
                    f"filter={filter_name} "
                    f"verdict={stability}"
                )

    print("VERDICT=EDGE_STABILITY_REPORT_V1_1_REAL_PF_READY")
    print("TEST_EDGE_STABILITY_REPORT_V1_1_REAL_PF_OK")
    return 0


if __name__ == "__main__":
    sys.exit(main())
