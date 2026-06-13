#!/usr/bin/env python3
# Отчёт качества закрытых сделок v1.1.
# Добавлены фильтры source/trade_source/strategy/timeframe и разрез ALL/BUY/SELL.

from __future__ import annotations

import argparse
import os
from decimal import Decimal

import psycopg2


def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument("--symbols", required=True)
    parser.add_argument("--source", default=None)
    parser.add_argument("--trade-source", default=None)
    parser.add_argument("--strategy", default=None)
    parser.add_argument("--timeframe", default=None)
    return parser.parse_args()


def get_conn():
    dsn = os.getenv("DATABASE_URL")
    if not dsn:
        raise RuntimeError("DATABASE_URL is not set")
    return psycopg2.connect(dsn)


def fmt(value):
    if value is None:
        return "None"
    if isinstance(value, Decimal):
        return f"{float(value):.8f}"
    if isinstance(value, float):
        return f"{value:.8f}"
    return str(value)


def build_where(args, symbols):
    clauses = ["symbol = ANY(%s)"]
    params = [symbols]

    if args.source:
        clauses.append("source = %s")
        params.append(args.source)

    if args.trade_source:
        clauses.append("trade_source = %s")
        params.append(args.trade_source)

    if args.strategy:
        clauses.append("strategy = %s")
        params.append(args.strategy)

    if args.timeframe:
        clauses.append("timeframe = %s")
        params.append(args.timeframe)

    return " AND ".join(clauses), params


def print_row(scope, row):
    symbol, side_bucket, trades, wins, losses, net_pnl, avg_pnl, gross_profit, gross_loss, worst_trade, best_trade = row

    winrate = float(wins or 0) / float(trades or 1)
    profit_factor = None
    if gross_loss and float(gross_loss) != 0.0:
        profit_factor = float(gross_profit or 0) / float(gross_loss)

    print(
        f"{scope}_ROW "
        f"symbol={symbol} "
        f"side={side_bucket} "
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


def main():
    args = parse_args()
    symbols = [s.strip() for s in args.symbols.split(",") if s.strip()]

    where_sql, params = build_where(args, symbols)

    print("=== CLOSED TRADES QUALITY REPORT V1.1 ===")
    print(f"symbols={','.join(symbols)}")
    print(f"source={args.source}")
    print(f"trade_source={args.trade_source}")
    print(f"strategy={args.strategy}")
    print(f"timeframe={args.timeframe}")
    print("pnl_column=net_pnl")
    print()

    symbol_sql = f"""
        WITH filtered AS (
            SELECT
                symbol,
                side,
                net_pnl
            FROM closed_trades
            WHERE {where_sql}
        ),
        expanded AS (
            SELECT symbol, 'ALL' AS side_bucket, net_pnl FROM filtered
            UNION ALL
            SELECT symbol, UPPER(side) AS side_bucket, net_pnl FROM filtered
        )
        SELECT
            symbol,
            side_bucket,
            COUNT(*) AS trades,
            SUM(CASE WHEN net_pnl > 0 THEN 1 ELSE 0 END) AS wins,
            SUM(CASE WHEN net_pnl < 0 THEN 1 ELSE 0 END) AS losses,
            SUM(net_pnl) AS net_pnl,
            AVG(net_pnl) AS avg_pnl,
            SUM(CASE WHEN net_pnl > 0 THEN net_pnl ELSE 0 END) AS gross_profit,
            ABS(SUM(CASE WHEN net_pnl < 0 THEN net_pnl ELSE 0 END)) AS gross_loss,
            MIN(net_pnl) AS worst_trade,
            MAX(net_pnl) AS best_trade
        FROM expanded
        GROUP BY symbol, side_bucket
        ORDER BY symbol, CASE side_bucket WHEN 'ALL' THEN 0 WHEN 'BUY' THEN 1 WHEN 'SELL' THEN 2 ELSE 3 END
    """

    total_sql = f"""
        WITH filtered AS (
            SELECT
                side,
                net_pnl
            FROM closed_trades
            WHERE {where_sql}
        ),
        expanded AS (
            SELECT 'TOTAL' AS symbol, 'ALL' AS side_bucket, net_pnl FROM filtered
            UNION ALL
            SELECT 'TOTAL' AS symbol, UPPER(side) AS side_bucket, net_pnl FROM filtered
        )
        SELECT
            symbol,
            side_bucket,
            COUNT(*) AS trades,
            SUM(CASE WHEN net_pnl > 0 THEN 1 ELSE 0 END) AS wins,
            SUM(CASE WHEN net_pnl < 0 THEN 1 ELSE 0 END) AS losses,
            SUM(net_pnl) AS net_pnl,
            AVG(net_pnl) AS avg_pnl,
            SUM(CASE WHEN net_pnl > 0 THEN net_pnl ELSE 0 END) AS gross_profit,
            ABS(SUM(CASE WHEN net_pnl < 0 THEN net_pnl ELSE 0 END)) AS gross_loss,
            MIN(net_pnl) AS worst_trade,
            MAX(net_pnl) AS best_trade
        FROM expanded
        GROUP BY symbol, side_bucket
        ORDER BY CASE side_bucket WHEN 'ALL' THEN 0 WHEN 'BUY' THEN 1 WHEN 'SELL' THEN 2 ELSE 3 END
    """

    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(symbol_sql, params)
            rows = cur.fetchall()

            if not rows:
                print("VERDICT=NO_CLOSED_TRADES_FOUND")
                return

            for row in rows:
                print_row("SYMBOL", row)

            print()
            cur.execute(total_sql, params)
            for row in cur.fetchall():
                print_row("TOTAL", row)

    print()
    print("VERDICT=OK")


if __name__ == "__main__":
    main()
