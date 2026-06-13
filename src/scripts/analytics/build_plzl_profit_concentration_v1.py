#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from __future__ import annotations

import os
from collections import defaultdict

import psycopg
from psycopg.rows import dict_row

SYMBOL = os.getenv("SYMBOL", "PLZL@MISX")


def pct(part, total):
    if abs(total) < 1e-12:
        return 0.0
    return part / total


def main():
    db = os.getenv("DATABASE_URL")
    if not db:
        raise SystemExit("DATABASE_URL_NOT_SET")

    with psycopg.connect(db, row_factory=dict_row) as conn:
        rows = list(
            conn.execute(
                """
                SELECT
                    pnl_points,
                    entry_ts,
                    exit_ts
                FROM analytics_closed_trades_v1
                WHERE symbol=%s
                ORDER BY exit_ts
                """,
                (SYMBOL,),
            )
        )

    pnls = [float(r["pnl_points"] or 0.0) for r in rows]

    total_trades = len(rows)
    total_pnl = sum(pnls)

    sorted_trades = sorted(pnls, reverse=True)

    top1_trade = sum(sorted_trades[:1])
    top5_trade = sum(sorted_trades[:5])
    top10_trade = sum(sorted_trades[:10])

    by_date = defaultdict(float)

    for r in rows:
        exit_ts = r["exit_ts"]
        pnl = float(r["pnl_points"] or 0.0)

        d = exit_ts.astimezone().date().isoformat()
        by_date[d] += pnl

    date_rows = sorted(
        by_date.items(),
        key=lambda x: x[1],
        reverse=True,
    )

    top1_day = sum(v for _, v in date_rows[:1])
    top3_day = sum(v for _, v in date_rows[:3])
    top5_day = sum(v for _, v in date_rows[:5])

    positive_dates = len([v for v in by_date.values() if v > 0])
    negative_dates = len([v for v in by_date.values() if v < 0])

    flags = []

    if pct(top1_trade, total_pnl) > 0.20:
        flags.append("TOP1_TRADE_CONCENTRATION")

    if pct(top5_trade, total_pnl) > 0.50:
        flags.append("TOP5_TRADE_CONCENTRATION")

    if pct(top10_trade, total_pnl) > 0.70:
        flags.append("TOP10_TRADE_CONCENTRATION")

    if pct(top1_day, total_pnl) > 0.30:
        flags.append("TOP1_DAY_CONCENTRATION")

    if pct(top3_day, total_pnl) > 0.60:
        flags.append("TOP3_DAY_CONCENTRATION")

    if positive_dates <= 1:
        flags.append("INSUFFICIENT_POSITIVE_DAYS")

    if flags:
        verdict = "EDGE_CONCENTRATED"
    else:
        verdict = "EDGE_DISTRIBUTED"

    print("=== PLZL PROFIT CONCENTRATION AUDIT V1 ===")
    print(f"symbol={SYMBOL}")
    print()

    print("SUMMARY")
    print(f"closed_trades={total_trades}")
    print(f"total_pnl={total_pnl:.6f}")
    print()

    print("TRADE_CONCENTRATION")
    print(f"top_1_trade_pnl={top1_trade:.6f}")
    print(f"top_1_trade_share={pct(top1_trade,total_pnl):.6f}")

    print(f"top_5_trade_pnl={top5_trade:.6f}")
    print(f"top_5_trade_share={pct(top5_trade,total_pnl):.6f}")

    print(f"top_10_trade_pnl={top10_trade:.6f}")
    print(f"top_10_trade_share={pct(top10_trade,total_pnl):.6f}")
    print()

    print("DAY_CONCENTRATION")
    print(f"top_1_day_pnl={top1_day:.6f}")
    print(f"top_1_day_share={pct(top1_day,total_pnl):.6f}")

    print(f"top_3_day_pnl={top3_day:.6f}")
    print(f"top_3_day_share={pct(top3_day,total_pnl):.6f}")

    print(f"top_5_day_pnl={top5_day:.6f}")
    print(f"top_5_day_share={pct(top5_day,total_pnl):.6f}")
    print()

    print("DATE_DISTRIBUTION")
    print(f"positive_dates={positive_dates}")
    print(f"negative_dates={negative_dates}")
    print(f"total_dates={len(by_date)}")
    print()

    print("TOP_DATES")
    for d, pnl in date_rows[:10]:
        print(f"date={d} pnl={pnl:.6f}")

    print()
    print("VERDICT")
    print(f"status={verdict}")
    print(f"flags={','.join(flags) if flags else 'none'}")


if __name__ == "__main__":
    main()
