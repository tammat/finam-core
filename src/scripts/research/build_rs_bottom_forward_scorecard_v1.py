#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
from decimal import Decimal

import psycopg
from psycopg.rows import dict_row


HISTORICAL_EDGE = {
    ("BOTTOM1", "COMPRESSION_RANGE"): {
        "historical_pf": Decimal("1.5233"),
        "historical_avg_return_pct": Decimal("0.199297"),
    },
    ("BOTTOM1", "REVERSAL_UP_CLOSE"): {
        "historical_pf": Decimal("1.4019"),
        "historical_avg_return_pct": Decimal("0.157168"),
    },
    ("BOTTOM1", "ALL"): {
        "historical_pf": Decimal("1.3903"),
        "historical_avg_return_pct": Decimal("0.150831"),
    },
    ("BOTTOM3", "REVERSAL_UP_CLOSE"): {
        "historical_pf": Decimal("1.3575"),
        "historical_avg_return_pct": Decimal("0.129750"),
    },
    ("BOTTOM3", "COMPRESSION_RANGE"): {
        "historical_pf": Decimal("1.3434"),
        "historical_avg_return_pct": Decimal("0.131941"),
    },
}


def dec(v):
    if v is None:
        return None
    return Decimal(str(v))


def pct_deviation(current, base):
    if current is None or base is None or base == 0:
        return None
    return (current - base) / base * Decimal("100")


def verdict(signals_total, forward_pf, historical_pf):
    if signals_total < 30:
        return "СБОР_СТАТИСТИКИ"
    if forward_pf is None:
        return "СБОР_СТАТИСТИКИ"
    if forward_pf >= historical_pf:
        return "EDGE_ПОДТВЕРЖДЕН"
    if forward_pf >= historical_pf * Decimal("0.9"):
        return "ПОДТВЕРЖДЕНИЕ_EDGE"
    if forward_pf < historical_pf * Decimal("0.5"):
        return "EDGE_СЛОМАН"
    if forward_pf < historical_pf * Decimal("0.7"):
        return "EDGE_УХУДШАЕТСЯ"
    return "СБОР_СТАТИСТИКИ"


def migrate(cur):
    cur.execute("""
        create table if not exists analytics_futures_rs_bottom_forward_scorecard_v1 (
            id bigserial primary key,
            created_at timestamptz not null default now(),
            selection text not null,
            filter_name text not null,
            signals_total integer not null,
            waiting integer not null,
            success integer not null,
            failure integer not null,
            completed integer not null,
            winrate numeric,
            avg_return_pct numeric,
            profit_factor_forward numeric,
            profit_factor_historical numeric,
            historical_avg_return_pct numeric,
            pf_deviation_pct numeric,
            return_deviation_pct numeric,
            verdict text not null,
            unique(selection, filter_name)
        );
    """)


def main() -> int:
    dsn = os.getenv("DATABASE_URL")
    if not dsn:
        raise SystemExit("DATABASE_URL_NOT_SET")

    with psycopg.connect(dsn, row_factory=dict_row) as conn:
        with conn.cursor() as cur:
            migrate(cur)

            rows_saved = 0

            for (selection, filter_name), hist in HISTORICAL_EDGE.items():
                cur.execute("""
                    select
                        count(*)::int as signals_total,
                        count(*) filter (where status='WAITING')::int as waiting,
                        count(*) filter (where status='SUCCESS')::int as success,
                        count(*) filter (where status='FAILURE')::int as failure,
                        count(*) filter (where status in ('SUCCESS','FAILURE'))::int as completed,
                        avg(return_pct) filter (where status in ('SUCCESS','FAILURE')) as avg_return_pct,
                        sum(return_pct) filter (where status='SUCCESS') as gross_profit,
                        abs(sum(return_pct) filter (where status='FAILURE')) as gross_loss
                    from analytics_futures_rs_bottom_paper_observation_v1
                    where selection = %s
                      and filter_name = %s
                """, (selection, filter_name))
                r = cur.fetchone()

                signals_total = int(r["signals_total"] or 0)
                waiting = int(r["waiting"] or 0)
                success = int(r["success"] or 0)
                failure = int(r["failure"] or 0)
                completed = int(r["completed"] or 0)

                winrate = None
                if completed > 0:
                    winrate = Decimal(success) / Decimal(completed)

                avg_return_pct = dec(r["avg_return_pct"])
                gross_profit = dec(r["gross_profit"]) or Decimal("0")
                gross_loss = dec(r["gross_loss"]) or Decimal("0")

                pf_forward = None
                if gross_loss > 0:
                    pf_forward = gross_profit / gross_loss
                elif gross_profit > 0 and gross_loss == 0:
                    pf_forward = Decimal("999")

                historical_pf = hist["historical_pf"]
                historical_avg = hist["historical_avg_return_pct"]

                pf_dev = pct_deviation(pf_forward, historical_pf)
                ret_dev = pct_deviation(avg_return_pct, historical_avg)

                row_verdict = verdict(signals_total, pf_forward, historical_pf)

                cur.execute("""
                    insert into analytics_futures_rs_bottom_forward_scorecard_v1 (
                        selection, filter_name,
                        signals_total, waiting, success, failure, completed,
                        winrate, avg_return_pct,
                        profit_factor_forward, profit_factor_historical,
                        historical_avg_return_pct,
                        pf_deviation_pct, return_deviation_pct,
                        verdict
                    )
                    values (
                        %(selection)s, %(filter_name)s,
                        %(signals_total)s, %(waiting)s, %(success)s, %(failure)s, %(completed)s,
                        %(winrate)s, %(avg_return_pct)s,
                        %(profit_factor_forward)s, %(profit_factor_historical)s,
                        %(historical_avg_return_pct)s,
                        %(pf_deviation_pct)s, %(return_deviation_pct)s,
                        %(verdict)s
                    )
                    on conflict (selection, filter_name)
                    do update set
                        created_at = now(),
                        signals_total = excluded.signals_total,
                        waiting = excluded.waiting,
                        success = excluded.success,
                        failure = excluded.failure,
                        completed = excluded.completed,
                        winrate = excluded.winrate,
                        avg_return_pct = excluded.avg_return_pct,
                        profit_factor_forward = excluded.profit_factor_forward,
                        profit_factor_historical = excluded.profit_factor_historical,
                        historical_avg_return_pct = excluded.historical_avg_return_pct,
                        pf_deviation_pct = excluded.pf_deviation_pct,
                        return_deviation_pct = excluded.return_deviation_pct,
                        verdict = excluded.verdict
                """, {
                    "selection": selection,
                    "filter_name": filter_name,
                    "signals_total": signals_total,
                    "waiting": waiting,
                    "success": success,
                    "failure": failure,
                    "completed": completed,
                    "winrate": winrate,
                    "avg_return_pct": avg_return_pct,
                    "profit_factor_forward": pf_forward,
                    "profit_factor_historical": historical_pf,
                    "historical_avg_return_pct": historical_avg,
                    "pf_deviation_pct": pf_dev,
                    "return_deviation_pct": ret_dev,
                    "verdict": row_verdict,
                })

                rows_saved += 1

                print(
                    "RS_BOTTOM_FORWARD_ROW "
                    f"selection={selection} filter={filter_name} "
                    f"signals_total={signals_total} waiting={waiting} "
                    f"success={success} failure={failure} completed={completed} "
                    f"pf_forward={pf_forward} pf_historical={historical_pf} "
                    f"avg_return_pct={avg_return_pct} verdict={row_verdict}"
                )

            conn.commit()

            cur.execute("""
                select count(*)::int as c
                from analytics_futures_rs_bottom_forward_scorecard_v1
            """)
            total_rows = cur.fetchone()["c"]

    print("=== RS_BOTTOM_FORWARD_SCORECARD_V1 ===")
    print("mode=save")
    print("db_update=1")
    print("runtime_changed=0")
    print("execution_changed=0")
    print("telegram_send=0")
    print(f"rows_saved={rows_saved}")
    print(f"scorecard_rows_total={total_rows}")
    print("VERDICT=RS_BOTTOM_FORWARD_SCORECARD_READY")
    print("TEST_RS_BOTTOM_FORWARD_SCORECARD_V1_OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
