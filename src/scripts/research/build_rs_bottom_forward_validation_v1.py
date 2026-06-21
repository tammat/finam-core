#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
from decimal import Decimal

import psycopg
from psycopg.rows import dict_row


MIN_COMPLETED_FOR_EARLY_READ = 10
MIN_COMPLETED_FOR_DECISION = 30
MIN_FORWARD_PF_CONFIRM = Decimal("1.15")


def dec(v):
    if v is None:
        return None
    return Decimal(str(v))


def verdict(completed, pf_forward, pf_historical):
    if completed < MIN_COMPLETED_FOR_EARLY_READ:
        return "СБОР_СТАТИСТИКИ"

    if completed < MIN_COMPLETED_FOR_DECISION:
        return "РАННЯЯ_ОЦЕНКА"

    if pf_forward is None:
        return "НЕТ_PF_FORWARD"

    pf_forward = dec(pf_forward)
    pf_historical = dec(pf_historical)

    if pf_forward >= MIN_FORWARD_PF_CONFIRM and pf_historical and pf_forward >= pf_historical * Decimal("0.70"):
        return "EDGE_ПОДТВЕРЖДАЕТСЯ"

    if pf_forward >= Decimal("1.00"):
        return "EDGE_СЛАБЫЙ"

    return "EDGE_НЕ_ПОДТВЕРЖДЕН"


def main() -> int:
    dsn = os.getenv("DATABASE_URL")
    if not dsn:
        raise SystemExit("DATABASE_URL_NOT_SET")

    print("=== RS_BOTTOM_FORWARD_VALIDATION_V1 ===")
    print("mode=read_only")
    print("db_update=0")
    print("runtime_changed=0")
    print("execution_changed=0")
    print("telegram_send=0")

    with psycopg.connect(dsn, row_factory=dict_row) as conn:
        with conn.cursor() as cur:
            cur.execute("""
                select
                    selection,
                    filter_name,
                    signals_total,
                    waiting,
                    success,
                    failure,
                    completed,
                    winrate,
                    avg_return_pct,
                    profit_factor_forward,
                    profit_factor_historical,
                    historical_avg_return_pct
                from analytics_futures_rs_bottom_forward_scorecard_v1
                order by profit_factor_historical desc nulls last, selection, filter_name
            """)
            rows = list(cur.fetchall())

    ready_for_decision = 0
    collecting = 0

    for r in rows:
        completed = int(r["completed"] or 0)
        v = verdict(completed, r["profit_factor_forward"], r["profit_factor_historical"])

        if completed >= MIN_COMPLETED_FOR_DECISION:
            ready_for_decision += 1
        else:
            collecting += 1

        print(
            "RS_BOTTOM_FORWARD_VALIDATION_ROW "
            f"selection={r['selection']} "
            f"filter={r['filter_name']} "
            f"signals_total={r['signals_total']} "
            f"waiting={r['waiting']} "
            f"success={r['success']} "
            f"failure={r['failure']} "
            f"completed={completed} "
            f"winrate={r['winrate']} "
            f"avg_return_pct={r['avg_return_pct']} "
            f"pf_forward={r['profit_factor_forward']} "
            f"pf_historical={r['profit_factor_historical']} "
            f"verdict={v}"
        )

    print(f"rows_total={len(rows)}")
    print(f"ready_for_decision={ready_for_decision}")
    print(f"collecting={collecting}")

    if ready_for_decision > 0:
        print("VERDICT=RS_BOTTOM_FORWARD_VALIDATION_DECISION_READY")
    else:
        print("VERDICT=RS_BOTTOM_FORWARD_VALIDATION_COLLECTING")

    print("TEST_RS_BOTTOM_FORWARD_VALIDATION_V1_OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
