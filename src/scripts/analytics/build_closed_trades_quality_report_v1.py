#!/usr/bin/env python3
# Отчёт качества закрытых сделок v1.
# Читает уже материализованные closed trades и считает базовую статистику по символам.

from __future__ import annotations

import argparse
import os
import psycopg2
from decimal import Decimal


def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument("--symbols", required=True, help="Например: NGN6@RTSX,BRN6@RTSX")
    return parser.parse_args()


def get_conn():
    dsn = os.getenv("DATABASE_URL")
    if not dsn:
        raise RuntimeError("DATABASE_URL is not set")
    return psycopg2.connect(dsn)


def fmt(x):
    if x is None:
        return "None"
    if isinstance(x, Decimal):
        return f"{float(x):.6f}"
    return str(x)


def main():
    args = parse_args()
    symbols = [s.strip() for s in args.symbols.split(",") if s.strip()]

    print("=== CLOSED TRADES QUALITY REPORT V1 ===")
    print(f"symbols={','.join(symbols)}")
    print()

    pnl_candidates = [
        "pnl",
        "net_pnl",
        "realized_pnl",
        "pnl_points",
        "profit",
        "result",
    ]

    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT column_name
                FROM information_schema.columns
                WHERE table_name = 'closed_trades'
                """
            )
            existing_columns = {r[0] for r in cur.fetchall()}

            pnl_col = next((c for c in pnl_candidates if c in existing_columns), None)

            if pnl_col is None:
                print("VERDICT=NO_PNL_COLUMN_FOUND")
                print("existing_columns=" + ",".join(sorted(existing_columns)))
                return

            print(f"pnl_column={pnl_col}")
            print()

            sql = f"""
                SELECT
                    symbol,
                    COUNT(*) AS trades,
                    SUM(CASE WHEN {pnl_col} > 0 THEN 1 ELSE 0 END) AS wins,
                    SUM(CASE WHEN {pnl_col} < 0 THEN 1 ELSE 0 END) AS losses,
                    SUM({pnl_col}) AS net_pnl,
                    AVG({pnl_col}) AS avg_pnl,
                    SUM(CASE WHEN {pnl_col} > 0 THEN {pnl_col} ELSE 0 END) AS gross_profit,
                    ABS(SUM(CASE WHEN {pnl_col} < 0 THEN {pnl_col} ELSE 0 END)) AS gross_loss,
                    MIN({pnl_col}) AS worst_trade,
                    MAX({pnl_col}) AS best_trade
                FROM closed_trades
                WHERE symbol = ANY(%s)
                GROUP BY symbol
                ORDER BY symbol
            """

            total_sql = f"""
                SELECT
                    COUNT(*) AS trades,
                    SUM(CASE WHEN {pnl_col} > 0 THEN 1 ELSE 0 END) AS wins,
                    SUM(CASE WHEN {pnl_col} < 0 THEN 1 ELSE 0 END) AS losses,
                    SUM({pnl_col}) AS net_pnl,
                    AVG({pnl_col}) AS avg_pnl,
                    SUM(CASE WHEN {pnl_col} > 0 THEN {pnl_col} ELSE 0 END) AS gross_profit,
                    ABS(SUM(CASE WHEN {pnl_col} < 0 THEN {pnl_col} ELSE 0 END)) AS gross_loss,
                    MIN({pnl_col}) AS worst_trade,
                    MAX({pnl_col}) AS best_trade
                FROM closed_trades
                WHERE symbol = ANY(%s)
            """

            cur.execute(sql, (symbols,))
            rows = cur.fetchall()

            if not rows:
                print("VERDICT=NO_CLOSED_TRADES_FOUND")
                return

            for row in rows:
                symbol, trades, wins, losses, net_pnl, avg_pnl, gross_profit, gross_loss, worst_trade, best_trade = row
                winrate = float(wins or 0) / float(trades or 1)
                profit_factor = None
                if gross_loss and gross_loss != 0:
                    profit_factor = gross_profit / gross_loss

                print(
                    "SYMBOL_ROW "
                    f"symbol={symbol} "
                    f"trades={trades} "
                    f"wins={wins or 0} "
                    f"losses={losses or 0} "
                    f"winrate={winrate:.4f} "
                    f"net_pnl={fmt(net_pnl)} "
                    f"avg_pnl={fmt(avg_pnl)} "
                    f"profit_factor={fmt(profit_factor)} "
                    f"worst_trade={fmt(worst_trade)} "
                    f"best_trade={fmt(best_trade)}"
                )

            print()
            cur.execute(total_sql, (symbols,))
            row = cur.fetchone()

            trades, wins, losses, net_pnl, avg_pnl, gross_profit, gross_loss, worst_trade, best_trade = row
            winrate = float(wins or 0) / float(trades or 1)
            profit_factor = None
            if gross_loss and gross_loss != 0:
                profit_factor = gross_profit / gross_loss

            print(
                "TOTAL_ROW "
                f"trades={trades} "
                f"wins={wins or 0} "
                f"losses={losses or 0} "
                f"winrate={winrate:.4f} "
                f"net_pnl={fmt(net_pnl)} "
                f"avg_pnl={fmt(avg_pnl)} "
                f"profit_factor={fmt(profit_factor)} "
                f"worst_trade={fmt(worst_trade)} "
                f"best_trade={fmt(best_trade)}"
            )

    print("VERDICT=OK")


if __name__ == "__main__":
    main()
