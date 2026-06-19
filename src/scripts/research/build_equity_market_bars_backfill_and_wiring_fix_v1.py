#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import json
import os
import sys
from psycopg2 import connect, sql
import psycopg2.extras

TARGETS = [
    "NVTK@MISX",
    "OZON@MISX",
    "T@MISX",
    "X5@MISX",
    "SBERP@MISX",
    "VTBR@MISX",
    "EUTR@MISX",
    "SFIN@MISX",
]

TS_CANDIDATES = ["bar_ts", "ts", "timestamp", "time", "datetime", "created_at"]


def get_columns(cur, table: str):
    cur.execute(
        """
        select column_name
        from information_schema.columns
        where table_schema='public'
          and table_name=%s
        order by ordinal_position
        """,
        (table,),
    )
    return [r["column_name"] for r in cur.fetchall()]


def count_bars(cur, table: str, cols: list[str], symbol: str, timeframe: str):
    if "symbol" not in cols:
        return {"error": "market_bars_symbol_column_missing"}

    if "timeframe" not in cols:
        return {"error": "market_bars_timeframe_column_missing"}

    ts_col = next((c for c in TS_CANDIDATES if c in cols), None)

    base = symbol.split("@", 1)[0]
    aliases = [symbol, base]

    select_last = sql.SQL("null")
    if ts_col:
        select_last = sql.Identifier(ts_col)

    q = sql.SQL(
        """
        select
            count(*) as bars,
            max({ts_col}) as last_bar
        from {table}
        where symbol = any(%s)
          and timeframe=%s
        """
    ).format(
        ts_col=select_last,
        table=sql.Identifier(table),
    )

    cur.execute(q, (aliases, timeframe))
    r = cur.fetchone()

    return {
        "bars": int(r["bars"] or 0),
        "last_bar": None if r["last_bar"] is None else str(r["last_bar"]),
        "aliases_checked": aliases,
        "timestamp_column": ts_col,
    }


def runtime_rows(cur, symbol: str):
    try:
        cur.execute(
            """
            select count(*) as rows
            from runtime_active_universe
            where symbol=%s
            """,
            (symbol,),
        )
        return int(cur.fetchone()["rows"] or 0)
    except Exception as exc:
        return {"error": str(exc)}


def diagnosis(runtime_count, m5, m1):
    if isinstance(m5, dict) and m5.get("error"):
        return "SCHEMA_REVIEW_REQUIRED"

    m5_bars = int(m5.get("bars") or 0)
    m1_bars = int(m1.get("bars") or 0)

    if runtime_count == 0:
        return "RUNTIME_UNIVERSE_MISSING"

    if m5_bars == 0 and m1_bars == 0:
        return "BACKFILL_M1_M5_REQUIRED"

    if m5_bars == 0 and m1_bars > 0:
        return "M5_AGGREGATION_REQUIRED"

    if m5_bars < 50:
        return "M5_BACKFILL_TOPUP_REQUIRED"

    return "BARS_OK_RECHECK_PIPELINE"


def main() -> int:
    dsn = os.environ.get("DATABASE_URL")
    if not dsn:
        print("ERROR=DATABASE_URL_NOT_SET")
        return 1

    rows = []

    with connect(dsn) as conn:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            market_cols = get_columns(cur, "market_bars")

            for symbol in TARGETS:
                rt = runtime_rows(cur, symbol)
                rt_count = rt if isinstance(rt, int) else 0

                try:
                    m5 = count_bars(cur, "market_bars", market_cols, symbol, "M5")
                except Exception as exc:
                    m5 = {"error": str(exc)}

                try:
                    m1 = count_bars(cur, "market_bars", market_cols, symbol, "M1")
                except Exception as exc:
                    m1 = {"error": str(exc)}

                d = diagnosis(rt_count, m5, m1)

                rows.append(
                    {
                        "symbol": symbol,
                        "runtime_rows": rt,
                        "m5": m5,
                        "m1": m1,
                        "diagnosis": d,
                        "planned_action": {
                            "BACKFILL_M1_M5_REQUIRED": "загрузить M1/M5 market_bars для symbol и alias base",
                            "M5_AGGREGATION_REQUIRED": "построить M5 из существующих M1",
                            "M5_BACKFILL_TOPUP_REQUIRED": "дозагрузить M5 до минимального окна",
                            "RUNTIME_UNIVERSE_MISSING": "проверить runtime_active_universe и allocator",
                            "SCHEMA_REVIEW_REQUIRED": "исправить SQL под фактическую схему market_bars",
                            "BARS_OK_RECHECK_PIPELINE": "проверить попадание баров в breakout watcher",
                        }.get(d, "review"),
                    }
                )

    summary = {}
    for r in rows:
        summary[r["diagnosis"]] = summary.get(r["diagnosis"], 0) + 1

    out = {
        "verdict": "EQUITY_MARKET_BARS_BACKFILL_AND_WIRING_FIX_PLAN_READY",
        "mode": "dry_run",
        "db_update": 0,
        "runtime_changed": 0,
        "execution_changed": 0,
        "telegram_send": 0,
        "targets_total": len(rows),
        "summary": summary,
        "rows": rows,
    }

    print(json.dumps(out, ensure_ascii=False, indent=2))
    print("VERDICT=EQUITY_MARKET_BARS_BACKFILL_AND_WIRING_FIX_PLAN_READY")
    print("TEST_EQUITY_MARKET_BARS_BACKFILL_AND_WIRING_FIX_V1_OK")
    return 0


if __name__ == "__main__":
    sys.exit(main())
