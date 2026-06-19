#!/usr/bin/env python3
from __future__ import annotations

import os
import psycopg
from psycopg.rows import dict_row


CANDIDATES = {
    "USDRUBF": [
        "USDRUBF@RTSX",
        "USDRUBF@FUT",
        "USDRUBF",
    ],
    "CNYRUB_TOD": [
        "CNYRUB_TOD@CETS",
        "CNYRUB_TOD@MISX",
        "CNYRUB_TOD",
        "CNYRUB_TOM@CETS",
        "CNYRUB_TOM",
    ],
    "IMOEX": [
        "IMOEX@MISX",
        "IMOEX@INDX",
        "IMOEX",
        "MOEX@MISX",
        "MOEXINDEX@MISX",
    ],
}


def table_exists(conn: psycopg.Connection, table_name: str) -> bool:
    with conn.cursor() as cur:
        cur.execute("select to_regclass(%s)", (table_name,))
        return cur.fetchone()[0] is not None


def find_symbol_stats(conn: psycopg.Connection, symbol: str) -> dict | None:
    with conn.cursor(row_factory=dict_row) as cur:
        cur.execute(
            """
            select
              symbol,
              timeframe,
              count(*)::int as bars,
              min(ts) as first_ts,
              max(ts) as last_ts
            from market_bars
            where symbol = %(symbol)s
            group by symbol, timeframe
            order by timeframe
            """,
            {"symbol": symbol},
        )
        rows = cur.fetchall()
        if not rows:
            return None
        return {
            "symbol": symbol,
            "rows": rows,
            "total_bars": sum(int(r["bars"]) for r in rows),
            "last_ts": max(r["last_ts"] for r in rows),
        }


def main() -> int:
    print("=== MULTI ASSET FX INDEX SYMBOL AUDIT V1 ===")
    print("mode=read_only_symbol_resolve")
    print(f"runtime_allow={os.getenv('RUNTIME_ALLOW_TRADING', '0')}")
    print(f"execution_enabled={os.getenv('EXECUTION_ENABLED', '0')}")
    print(f"real_trading_enabled={os.getenv('REAL_TRADING_ENABLED', '0')}")
    print("orders_create=0")
    print("execution_intents_create=0")
    print("real_execution=0")

    database_url = os.getenv("DATABASE_URL")
    if not database_url:
        raise SystemExit("DATABASE_URL is required")

    selected: dict[str, str] = {}

    with psycopg.connect(database_url) as conn:
        if not table_exists(conn, "market_bars"):
            print("MARKET_BARS_TABLE_MISSING")
            print("VERDICT=FX_INDEX_SYMBOL_AUDIT_FAILED_NO_MARKET_BARS")
            return 1

        print()
        print("FX_INDEX_SYMBOL_CANDIDATES")

        for logical_name, candidates in CANDIDATES.items():
            best_symbol = None
            best_bars = -1

            for symbol in candidates:
                stats = find_symbol_stats(conn, symbol)
                if not stats:
                    print(
                        "SYMBOL_CANDIDATE_ROW "
                        f"logical={logical_name} symbol={symbol} status=NO_BARS"
                    )
                    continue

                print(
                    "SYMBOL_CANDIDATE_ROW "
                    f"logical={logical_name} symbol={symbol} status=BARS_OK "
                    f"total_bars={stats['total_bars']} last_ts={stats['last_ts']}"
                )

                for r in stats["rows"]:
                    print(
                        "SYMBOL_TIMEFRAME_ROW "
                        f"logical={logical_name} symbol={symbol} timeframe={r['timeframe']} "
                        f"bars={r['bars']} first_ts={r['first_ts']} last_ts={r['last_ts']}"
                    )

                if stats["total_bars"] > best_bars:
                    best_bars = stats["total_bars"]
                    best_symbol = symbol

            if best_symbol:
                selected[logical_name] = best_symbol
                print(
                    "SYMBOL_SELECTED_ROW "
                    f"logical={logical_name} symbol={best_symbol} status=SELECTED bars={best_bars}"
                )
            else:
                print(
                    "SYMBOL_SELECTED_ROW "
                    f"logical={logical_name} symbol=NONE status=NO_AVAILABLE_MARKET_BARS"
                )

    print()
    print("FX_INDEX_SYMBOL_AUDIT_SUMMARY")
    print(f"selected_total={len(selected)}")
    for logical_name in ["USDRUBF", "CNYRUB_TOD", "IMOEX"]:
        print(f"selected_{logical_name}={selected.get(logical_name, 'NONE')}")

    if len(selected) == 3:
        print("VERDICT=FX_INDEX_SYMBOL_AUDIT_ALL_SYMBOLS_RESOLVED")
    else:
        print("VERDICT=FX_INDEX_SYMBOL_AUDIT_PARTIAL_SYMBOLS_RESOLVED")

    print("MULTI_ASSET_FX_INDEX_SYMBOL_AUDIT_V1_OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
