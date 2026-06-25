#!/usr/bin/env python3

import os
import psycopg2


FUTURES = [
    ("BRENT", "BR"),
    ("NATURAL_GAS", "NG"),
    ("GOLD", "GD"),
    ("SILVER", "SV"),
    ("USD_RUB", "USDRUBF"),
    ("CNY_RUB", "CNYRUBF"),
    ("EUR_RUB", "EURRUBF"),
]

EQUITIES = [
    "SBER", "SBERP", "LKOH", "GAZP", "NVTK", "T", "X5",
    "PLZL", "ROSN", "VTBR", "SIBN", "MAGN", "GMKN", "ALRS",
]

CONTEXTS = [
    ("IMOEX", "%IMOEX%"),
    ("RTSI", "%RTSI%"),
    ("USD_RUB", "%USD%"),
    ("BRENT", "%BR%"),
    ("GOLD", "%GD%"),
]


def scalar_row(cur, sql, params):
    cur.execute(sql, params)
    return cur.fetchone()


def main() -> int:
    print("=== UNIVERSE_DATA_COVERAGE_AUDIT_V1 ===")
    print("mode=audit_read_only")
    print("db_update=0")
    print("runtime_changed=0")
    print("execution_changed=0")
    print("real_trading_enabled=0")
    print("orders_sent=0")

    db = os.environ.get("DATABASE_URL", "")
    if not db:
        print("ERROR=DATABASE_URL_NOT_SET")
        return 2
    if db.startswith("sqlite"):
        print("ERROR=SQLITE_FORBIDDEN")
        return 2

    with psycopg2.connect(db) as conn:
        with conn.cursor() as cur:
            print("")
            print("FUTURES_COVERAGE")
            for name, family in FUTURES:
                pattern = f"{family}%@RTSX"
                bars, first_bar, last_bar = scalar_row(cur, """
                    SELECT COUNT(*), MIN(ts), MAX(ts)
                    FROM public.feature_snapshots
                    WHERE symbol LIKE %s;
                """, (pattern,))
                trades, first_trade, last_trade = scalar_row(cur, """
                    SELECT COUNT(*), MIN(entry_ts), MAX(entry_ts)
                    FROM public.closed_trades
                    WHERE symbol LIKE %s;
                """, (pattern,))
                print(
                    "FUTURES_ROW "
                    f"name={name} family={family} "
                    f"feature_rows={bars} first_feature={first_bar} last_feature={last_bar} "
                    f"closed_trades={trades} first_trade={first_trade} last_trade={last_trade}"
                )

            print("")
            print("EQUITY_COVERAGE")
            for ticker in EQUITIES:
                symbol = f"{ticker}@MISX"
                bars, first_bar, last_bar = scalar_row(cur, """
                    SELECT COUNT(*), MIN(ts), MAX(ts)
                    FROM public.feature_snapshots
                    WHERE symbol=%s;
                """, (symbol,))
                trades, first_trade, last_trade = scalar_row(cur, """
                    SELECT COUNT(*), MIN(entry_ts), MAX(entry_ts)
                    FROM public.closed_trades
                    WHERE symbol=%s;
                """, (symbol,))
                print(
                    "EQUITY_ROW "
                    f"ticker={ticker} symbol={symbol} "
                    f"feature_rows={bars} first_feature={first_bar} last_feature={last_bar} "
                    f"closed_trades={trades} first_trade={first_trade} last_trade={last_trade}"
                )

            print("")
            print("CONTEXT_COVERAGE")
            for code, pattern in CONTEXTS:
                rows, first_ts, last_ts = scalar_row(cur, """
                    SELECT COUNT(*), MIN(ts), MAX(ts)
                    FROM public.feature_snapshots
                    WHERE symbol ILIKE %s;
                """, (pattern,))
                print(
                    "CONTEXT_ROW "
                    f"code={code} pattern={pattern} "
                    f"feature_rows={rows} first_feature={first_ts} last_feature={last_ts}"
                )

            cur.execute("""
                SELECT COUNT(*)
                FROM public.closed_trades
                WHERE symbol IS NOT NULL
                  AND timeframe IS NOT NULL
                  AND entry_ts IS NOT NULL
                  AND net_pnl IS NOT NULL;
            """)
            closed_trades_usable = cur.fetchone()[0]

            cur.execute("""
                SELECT COUNT(*)
                FROM public.feature_snapshots
                WHERE symbol IS NOT NULL
                  AND timeframe IS NOT NULL
                  AND ts IS NOT NULL
                  AND close IS NOT NULL;
            """)
            feature_rows_usable = cur.fetchone()[0]

    print("")
    print("SUMMARY")
    print(f"closed_trades_usable={closed_trades_usable}")
    print(f"feature_rows_usable={feature_rows_usable}")

    print("")
    print("NEXT_STEPS")
    print("next=UNIVERSE_BACKFILL_PLAN_V1")
    print("next=GLOBAL_EDGE_DISCOVERY_V1")

    print("")
    print("VERDICT=UNIVERSE_DATA_COVERAGE_AUDIT_READY")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
