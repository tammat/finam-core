#!/usr/bin/env python3
from __future__ import annotations

import os
import psycopg
from psycopg.rows import dict_row


TARGETS = [
    {
        "symbol": "USDRUBF@RTSX",
        "display_name": "USD/RUB фьючерс",
        "asset_class": "FX_FUTURES",
        "timeframes": ["M5", "M1"],
        "roles": {"M5": "PRIMARY_WATCH", "M1": "INTRADAY_WATCH"},
        "orderable": False,
        "reason": "watch_only_fx_futures",
    },
    {
        "symbol": "CNYRUBF@RTSX",
        "display_name": "CNY/RUB фьючерс",
        "asset_class": "FX_FUTURES",
        "timeframes": ["M5", "M1"],
        "roles": {"M5": "PRIMARY_WATCH", "M1": "INTRADAY_WATCH"},
        "orderable": False,
        "reason": "watch_only_cny_futures",
    },
    {
        "symbol": "CNYRUB_TOM@MISX",
        "display_name": "Юань к рублю TOM",
        "asset_class": "FX_SPOT",
        "timeframes": ["M5", "M1"],
        "roles": {"M5": "PRIMARY_WATCH", "M1": "INTRADAY_WATCH"},
        "orderable": False,
        "reason": "watch_only_cny_tom_not_tod",
    },
]


MISSING_CONTEXT = [
    {
        "logical_name": "CNYRUB_TOD",
        "status": "NO_MARKET_BARS",
        "reason": "В market_bars нет CNYRUB_TOD; найден CNYRUB_TOM@MISX, но это TOM, не TOD.",
    },
    {
        "logical_name": "IMOEX",
        "status": "NO_MARKET_BARS",
        "reason": "В market_bars нет IMOEX/MOEX index; нужен отдельный index ingestion/backfill.",
    },
]


def fetch_bar_stats(conn: psycopg.Connection, symbol: str, timeframe: str) -> dict:
    with conn.cursor(row_factory=dict_row) as cur:
        cur.execute(
            """
            select
              count(*)::int as bars,
              min(ts) as first_ts,
              max(ts) as last_ts
            from market_bars
            where symbol = %(symbol)s
              and timeframe = %(timeframe)s
            """,
            {"symbol": symbol, "timeframe": timeframe},
        )
        row = cur.fetchone()
        return {
            "bars": int(row["bars"] or 0),
            "first_ts": row["first_ts"],
            "last_ts": row["last_ts"],
        }


def main() -> int:
    print("=== MULTI ASSET FX WATCHLIST EXTENSION V1 ===")
    print("mode=read_only_watchlist_extension_plan")
    print(f"runtime_allow={os.getenv('RUNTIME_ALLOW_TRADING', '0')}")
    print(f"execution_enabled={os.getenv('EXECUTION_ENABLED', '0')}")
    print(f"real_trading_enabled={os.getenv('REAL_TRADING_ENABLED', '0')}")
    print("orders_create=0")
    print("execution_intents_create=0")
    print("real_execution=0")
    print("db_update=0")

    database_url = os.getenv("DATABASE_URL")
    if not database_url:
        raise SystemExit("DATABASE_URL is required")

    planned_rows = []
    blocked_rows = []

    with psycopg.connect(database_url) as conn:
        print()
        print("FX_WATCHLIST_EXTENSION_ROWS")

        for target in TARGETS:
            for timeframe in target["timeframes"]:
                stats = fetch_bar_stats(conn, target["symbol"], timeframe)
                role = target["roles"][timeframe]
                status = "READY_TO_ADD" if stats["bars"] > 0 else "BLOCK_NO_BARS"

                print(
                    "FX_WATCHLIST_ROW "
                    f"symbol={target['symbol']} display_name='{target['display_name']}' "
                    f"asset_class={target['asset_class']} timeframe={timeframe} role={role} "
                    f"bars={stats['bars']} first_ts={stats['first_ts']} last_ts={stats['last_ts']} "
                    f"orderable={int(target['orderable'])} status={status} reason={target['reason']}"
                )

                row = {
                    **target,
                    "timeframe": timeframe,
                    "role": role,
                    "bars": stats["bars"],
                    "first_ts": stats["first_ts"],
                    "last_ts": stats["last_ts"],
                    "status": status,
                }
                if status == "READY_TO_ADD":
                    planned_rows.append(row)
                else:
                    blocked_rows.append(row)

        print()
        print("FX_WATCHLIST_MISSING_CONTEXT")
        for item in MISSING_CONTEXT:
            print(
                "FX_MISSING_ROW "
                f"logical_name={item['logical_name']} status={item['status']} reason='{item['reason']}'"
            )

    print()
    print("FX_WATCHLIST_EXTENSION_SUMMARY")
    print(f"planned_rows={len(planned_rows)}")
    print(f"blocked_rows={len(blocked_rows)}")
    print(f"missing_context_rows={len(MISSING_CONTEXT)}")
    print("runtime_changes_required=1")
    print("execution_changes_required=0")
    print("real_trading_enabled=0")
    print("execution_enabled=0")

    if planned_rows:
        print("VERDICT=MULTI_ASSET_FX_WATCHLIST_EXTENSION_PLAN_READY")
    else:
        print("VERDICT=MULTI_ASSET_FX_WATCHLIST_EXTENSION_NO_READY_SYMBOLS")

    print("MULTI_ASSET_FX_WATCHLIST_EXTENSION_V1_OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
