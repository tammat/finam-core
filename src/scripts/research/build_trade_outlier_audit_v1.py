#!/usr/bin/env python3

from __future__ import annotations
import os
import statistics
import psycopg2


def get_conn():
    dsn = os.getenv("DATABASE_URL")
    if not dsn:
        raise RuntimeError("DATABASE_URL is not set")
    return psycopg2.connect(dsn)


def profit_factor(values):
    gross_profit = sum(v for v in values if v > 0)
    gross_loss = abs(sum(v for v in values if v < 0))
    if gross_loss == 0:
        return None
    return gross_profit / gross_loss


def expectancy(values):
    return sum(values) / len(values) if values else 0.0


with get_conn() as conn:
    with conn.cursor() as cur:

        cur.execute("""
            select net_pnl
            from closed_trades
            where net_pnl is not null
        """)

        pnl = [float(r[0]) for r in cur.fetchall()]

        print("=== TRADE OUTLIER AUDIT V1 ===")

        if len(pnl) < 10:
            print(f"TRADES={len(pnl)}")
            print("VERDICT=INSUFFICIENT_DATA")
            raise SystemExit(0)

        abs_pnl = sorted(abs(x) for x in pnl)

        median_abs = statistics.median(abs_pnl)

        outliers = [
            x for x in pnl
            if abs(x) > median_abs * 5
        ]

        pf_raw = profit_factor(pnl)
        exp_raw = expectancy(pnl)

        wins_sorted = sorted(
            [x for x in pnl if x > 0],
            reverse=True
        )

        losses_sorted = sorted(
            [x for x in pnl if x < 0]
        )

        print()
        print(f"TRADES={len(pnl)}")
        print(f"MEDIAN_ABS_PNL={median_abs:.8f}")
        print(f"OUTLIERS={len(outliers)}")

        print()
        print(
            f"RAW "
            f"PF={pf_raw} "
            f"EXPECTANCY={exp_raw:.8f}"
        )

        for n in (1, 3, 5):

            pnl_no_top_win = pnl.copy()

            for v in wins_sorted[:n]:
                pnl_no_top_win.remove(v)

            pf = profit_factor(pnl_no_top_win)
            exp = expectancy(pnl_no_top_win)

            print(
                f"WITHOUT_TOP_{n}_WIN "
                f"PF={pf} "
                f"EXPECTANCY={exp:.8f}"
            )

        for n in (1, 3, 5):

            pnl_no_top_loss = pnl.copy()

            for v in losses_sorted[:n]:
                pnl_no_top_loss.remove(v)

            pf = profit_factor(pnl_no_top_loss)
            exp = expectancy(pnl_no_top_loss)

            print(
                f"WITHOUT_TOP_{n}_LOSS "
                f"PF={pf} "
                f"EXPECTANCY={exp:.8f}"
            )

        print()
        print("TOP_PROFITS")

        cur.execute("""
            select
                symbol,
                strategy,
                net_pnl
            from closed_trades
            where net_pnl is not null
            order by net_pnl desc
            limit 20
        """)

        for symbol, strategy, net_pnl in cur.fetchall():
            print(
                f"TOP_PROFIT_ROW "
                f"symbol={symbol} "
                f"strategy={strategy} "
                f"net_pnl={net_pnl}"
            )

        print()
        print("TOP_LOSSES")

        cur.execute("""
            select
                symbol,
                strategy,
                net_pnl
            from closed_trades
            where net_pnl is not null
            order by net_pnl asc
            limit 20
        """)

        for symbol, strategy, net_pnl in cur.fetchall():
            print(
                f"TOP_LOSS_ROW "
                f"symbol={symbol} "
                f"strategy={strategy} "
                f"net_pnl={net_pnl}"
            )

        print()
        print("VERDICT=OK")
