#!/usr/bin/env python3
# Отчёт качества closed_trades v1.2.
# Добавлены: проверка net_pnl ≈ gross_pnl - commission, median PnL,
# средний hold time, MAE/MFE, флаг TRADE_QUALITY_BAD.

from __future__ import annotations

import argparse
import os

import psycopg2


def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument("--symbols", required=True)
    parser.add_argument("--source", default=None)
    parser.add_argument("--trade-source", default=None)
    parser.add_argument("--strategy", default=None)
    parser.add_argument("--timeframe", default=None)
    parser.add_argument("--pnl-tolerance", type=float, default=0.000001)
    return parser.parse_args()


def get_conn():
    dsn = os.getenv("DATABASE_URL")
    if not dsn:
        raise RuntimeError("DATABASE_URL is not set")
    return psycopg2.connect(dsn)


def fmt(value):
    if value is None:
        return "None"
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


def quality_flag(net_pnl, profit_factor):
    if net_pnl is None:
        return "TRADE_QUALITY_BAD"
    if float(net_pnl) < 0:
        return "TRADE_QUALITY_BAD"
    if profit_factor is None:
        return "TRADE_QUALITY_BAD"
    if float(profit_factor) < 1.0:
        return "TRADE_QUALITY_BAD"
    return "TRADE_QUALITY_OK"


def print_row(scope, row):
    (
        symbol,
        side_bucket,
        trades,
        wins,
        losses,
        net_pnl,
        avg_pnl,
        median_pnl,
        gross_profit,
        gross_loss,
        worst_trade,
        best_trade,
        avg_hold_seconds,
        avg_mae,
        avg_mfe,
        pnl_mismatch_count,
        max_pnl_mismatch,
    ) = row

    winrate = float(wins or 0) / float(trades or 1)

    profit_factor = None
    if gross_loss and float(gross_loss) != 0.0:
        profit_factor = float(gross_profit or 0) / float(gross_loss)

    flag = quality_flag(net_pnl, profit_factor)

    print(
        f"{scope}_ROW "
        f"symbol={symbol} "
        f"side={side_bucket} "
        f"trades={trades} "
        f"wins={wins or 0} "
        f"losses={losses or 0} "
        f"winrate={winrate:.4f} "
        f"net_pnl={fmt(float(net_pnl or 0))} "
        f"avg_pnl={fmt(float(avg_pnl or 0))} "
        f"median_pnl={fmt(float(median_pnl or 0))} "
        f"profit_factor={fmt(profit_factor)} "
        f"worst_trade={fmt(float(worst_trade or 0))} "
        f"best_trade={fmt(float(best_trade or 0))} "
        f"avg_hold_seconds={fmt(float(avg_hold_seconds or 0))} "
        f"avg_mae={fmt(float(avg_mae or 0))} "
        f"avg_mfe={fmt(float(avg_mfe or 0))} "
        f"pnl_mismatch_count={pnl_mismatch_count or 0} "
        f"max_pnl_mismatch={fmt(float(max_pnl_mismatch or 0))} "
        f"quality_flag={flag}"
    )


def main():
    args = parse_args()
    symbols = [s.strip() for s in args.symbols.split(",") if s.strip()]
    where_sql, params = build_where(args, symbols)
    params_with_tol = params + [args.pnl_tolerance]

    print("=== CLOSED TRADES QUALITY REPORT V1.2 ===")
    print(f"symbols={','.join(symbols)}")
    print(f"source={args.source}")
    print(f"trade_source={args.trade_source}")
    print(f"strategy={args.strategy}")
    print(f"timeframe={args.timeframe}")
    print("pnl_column=net_pnl")
    print(f"pnl_tolerance={args.pnl_tolerance}")
    print()

    base_cte = f"""
        WITH filtered AS (
            SELECT
                symbol,
                UPPER(side) AS side,
                net_pnl::double precision AS net_pnl,
                gross_pnl::double precision AS gross_pnl,
                commission::double precision AS commission,
                COALESCE(holding_seconds, hold_seconds, 0)::double precision AS hold_seconds,
                COALESCE(mae, 0)::double precision AS mae,
                COALESCE(mfe, 0)::double precision AS mfe,
                ABS(net_pnl::double precision - (gross_pnl::double precision - commission::double precision)) AS pnl_mismatch
            FROM closed_trades
            WHERE {where_sql}
        ),
        expanded AS (
            SELECT
                symbol,
                'ALL' AS side_bucket,
                side,
                net_pnl,
                gross_pnl,
                commission,
                hold_seconds,
                mae,
                mfe,
                pnl_mismatch
            FROM filtered
            UNION ALL
            SELECT
                symbol,
                side AS side_bucket,
                side,
                net_pnl,
                gross_pnl,
                commission,
                hold_seconds,
                mae,
                mfe,
                pnl_mismatch
            FROM filtered
        )
    """

    select_sql = """
        SELECT
            symbol,
            side_bucket,
            COUNT(*) AS trades,
            SUM(CASE WHEN net_pnl > 0 THEN 1 ELSE 0 END) AS wins,
            SUM(CASE WHEN net_pnl < 0 THEN 1 ELSE 0 END) AS losses,
            SUM(net_pnl) AS net_pnl,
            AVG(net_pnl) AS avg_pnl,
            PERCENTILE_CONT(0.5) WITHIN GROUP (ORDER BY net_pnl) AS median_pnl,
            SUM(CASE WHEN net_pnl > 0 THEN net_pnl ELSE 0 END) AS gross_profit,
            ABS(SUM(CASE WHEN net_pnl < 0 THEN net_pnl ELSE 0 END)) AS gross_loss,
            MIN(net_pnl) AS worst_trade,
            MAX(net_pnl) AS best_trade,
            AVG(hold_seconds) AS avg_hold_seconds,
            AVG(mae) AS avg_mae,
            AVG(mfe) AS avg_mfe,
            SUM(CASE WHEN pnl_mismatch > %s THEN 1 ELSE 0 END) AS pnl_mismatch_count,
            MAX(pnl_mismatch) AS max_pnl_mismatch
        FROM expanded
        GROUP BY symbol, side_bucket
    """

    symbol_sql = base_cte + select_sql + """
        ORDER BY symbol,
            CASE side_bucket
                WHEN 'ALL' THEN 0
                WHEN 'LONG' THEN 1
                WHEN 'BUY' THEN 2
                WHEN 'SHORT' THEN 3
                WHEN 'SELL' THEN 4
                ELSE 5
            END
    """

    total_sql = base_cte + """
        SELECT
            'TOTAL' AS symbol,
            side_bucket,
            COUNT(*) AS trades,
            SUM(CASE WHEN net_pnl > 0 THEN 1 ELSE 0 END) AS wins,
            SUM(CASE WHEN net_pnl < 0 THEN 1 ELSE 0 END) AS losses,
            SUM(net_pnl) AS net_pnl,
            AVG(net_pnl) AS avg_pnl,
            PERCENTILE_CONT(0.5) WITHIN GROUP (ORDER BY net_pnl) AS median_pnl,
            SUM(CASE WHEN net_pnl > 0 THEN net_pnl ELSE 0 END) AS gross_profit,
            ABS(SUM(CASE WHEN net_pnl < 0 THEN net_pnl ELSE 0 END)) AS gross_loss,
            MIN(net_pnl) AS worst_trade,
            MAX(net_pnl) AS best_trade,
            AVG(hold_seconds) AS avg_hold_seconds,
            AVG(mae) AS avg_mae,
            AVG(mfe) AS avg_mfe,
            SUM(CASE WHEN pnl_mismatch > %s THEN 1 ELSE 0 END) AS pnl_mismatch_count,
            MAX(pnl_mismatch) AS max_pnl_mismatch
        FROM expanded
        GROUP BY side_bucket
        ORDER BY
            CASE side_bucket
                WHEN 'ALL' THEN 0
                WHEN 'LONG' THEN 1
                WHEN 'BUY' THEN 2
                WHEN 'SHORT' THEN 3
                WHEN 'SELL' THEN 4
                ELSE 5
            END
    """

    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(symbol_sql, params_with_tol)
            rows = cur.fetchall()

            if not rows:
                print("VERDICT=NO_CLOSED_TRADES_FOUND")
                return

            for row in rows:
                print_row("SYMBOL", row)

            print()
            cur.execute(total_sql, params_with_tol)
            for row in cur.fetchall():
                print_row("TOTAL", row)

    print()
    print("VERDICT=OK")


if __name__ == "__main__":
    main()
