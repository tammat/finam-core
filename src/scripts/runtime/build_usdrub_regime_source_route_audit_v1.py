#!/usr/bin/env python3
from __future__ import annotations

import os
from pathlib import Path
from typing import Any

import psycopg2
import psycopg2.extras


# Русский комментарий:
# USDRUB_REGIME_SOURCE_ROUTE_AUDIT_V1
# Read-only диагностика: откуда USDRUB_REGIME попадает в paper pipeline,
# если runtime_active_universe не содержит USDRUBF@RTSX / USDRUB_REGIME.


TARGET_SYMBOL = "USDRUBF@RTSX"
TARGET_STRATEGY = "USDRUB_REGIME"

SEARCH_ROOTS = [
    "src/finam_core/pipelines",
    "src/finam_core/strategy",
    "src/finam_core/runtime",
    "src/finam_core/execution",
    "src/scripts",
]

PATTERNS = [
    "USDRUB_REGIME",
    "USDRUBF@RTSX",
    "USDRUB_CONT",
    "USDRUB",
    "strategy_name_for_symbol",
    "_strategy_name_for_symbol",
    "runtime_strategy",
    "DEFAULT_STRATEGY",
    "SYMBOL_STRATEGY_MAP",
]


RUNTIME_ROWS_SQL = """
select *
from runtime_active_universe
where symbol = %s
   or strategy = %s
   or symbol ilike '%%USDRUB%%'
   or strategy ilike '%%USDRUB%%'
order by symbol, strategy, timeframe nulls last;
"""


TODAY_TRADES_SQL = """
select
    symbol,
    strategy,
    timeframe,
    continuous_symbol,
    trade_source,
    origin,
    count(*) as trades,
    min(created_at) as first_trade,
    max(created_at) as last_trade
from trades
where created_at::date = current_date
  and (
        symbol = %s
     or strategy = %s
     or symbol ilike '%%USDRUB%%'
     or strategy ilike '%%USDRUB%%'
  )
group by symbol, strategy, timeframe, continuous_symbol, trade_source, origin
order by trades desc, symbol, strategy, timeframe;
"""


RECENT_TRADES_SQL = """
select
    id,
    created_at,
    symbol,
    strategy,
    timeframe,
    continuous_symbol,
    side,
    qty,
    price,
    trade_source,
    origin,
    fill_id
from trades
where created_at::date = current_date
  and (
        symbol = %s
     or strategy = %s
     or symbol ilike '%%USDRUB%%'
     or strategy ilike '%%USDRUB%%'
  )
order by created_at desc, id desc
limit 10;
"""


def fmt(value: Any) -> str:
    if value is None:
        return "NULL"
    return str(value)


def scan_code() -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    repo = Path.cwd()

    for root in SEARCH_ROOTS:
        base = repo / root
        if not base.exists():
            continue

        for path in base.rglob("*.py"):
            try:
                text = path.read_text(encoding="utf-8", errors="ignore")
            except Exception:
                continue

            lines = text.splitlines()
            for i, line in enumerate(lines, start=1):
                for pattern in PATTERNS:
                    if pattern in line:
                        rows.append(
                            {
                                "file": str(path.relative_to(repo)),
                                "line": i,
                                "pattern": pattern,
                                "text": line.strip()[:240],
                            }
                        )
    return rows


def main() -> int:
    dsn = os.getenv("DATABASE_URL")
    if not dsn:
        raise SystemExit("DATABASE_URL is required")

    print("=== USDRUB REGIME SOURCE ROUTE AUDIT V1 ===")
    print("mode=read_only")
    print("runtime_allow=0")
    print("execution_enabled=0")
    print("real_trading_enabled=0")
    print("db_update=0")
    print(f"target_symbol={TARGET_SYMBOL}")
    print(f"target_strategy={TARGET_STRATEGY}")
    print()

    with psycopg2.connect(dsn) as conn:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute(RUNTIME_ROWS_SQL, (TARGET_SYMBOL, TARGET_STRATEGY))
            runtime_rows = cur.fetchall()

            cur.execute(TODAY_TRADES_SQL, (TARGET_SYMBOL, TARGET_STRATEGY))
            trade_rows = cur.fetchall()

            cur.execute(RECENT_TRADES_SQL, (TARGET_SYMBOL, TARGET_STRATEGY))
            recent_rows = cur.fetchall()

    code_hits = scan_code()

    print("USDRUB_SOURCE_RUNTIME_ROWS")
    for row in runtime_rows:
        print(
            "USDRUB_SOURCE_RUNTIME_ROW "
            f"symbol={fmt(row.get('symbol'))} "
            f"strategy={fmt(row.get('strategy'))} "
            f"timeframe={fmt(row.get('timeframe'))} "
            f"is_enabled={fmt(row.get('is_enabled'))} "
            f"source={fmt(row.get('source'))} "
            f"disable_reason={fmt(row.get('disable_reason'))}"
        )

    print()
    print("USDRUB_SOURCE_TRADE_ROWS")
    for row in trade_rows:
        print(
            "USDRUB_SOURCE_TRADE_ROW "
            f"symbol={fmt(row.get('symbol'))} "
            f"strategy={fmt(row.get('strategy'))} "
            f"timeframe={fmt(row.get('timeframe'))} "
            f"continuous_symbol={fmt(row.get('continuous_symbol'))} "
            f"trade_source={fmt(row.get('trade_source'))} "
            f"origin={fmt(row.get('origin'))} "
            f"trades={fmt(row.get('trades'))} "
            f"first_trade={fmt(row.get('first_trade'))} "
            f"last_trade={fmt(row.get('last_trade'))}"
        )

    print()
    print("USDRUB_SOURCE_RECENT_TRADES")
    for row in recent_rows:
        print(
            "USDRUB_SOURCE_RECENT_TRADE "
            f"id={fmt(row.get('id'))} "
            f"created_at={fmt(row.get('created_at'))} "
            f"symbol={fmt(row.get('symbol'))} "
            f"strategy={fmt(row.get('strategy'))} "
            f"timeframe={fmt(row.get('timeframe'))} "
            f"continuous_symbol={fmt(row.get('continuous_symbol'))} "
            f"side={fmt(row.get('side'))} "
            f"qty={fmt(row.get('qty'))} "
            f"price={fmt(row.get('price'))} "
            f"trade_source={fmt(row.get('trade_source'))} "
            f"origin={fmt(row.get('origin'))} "
            f"fill_id={fmt(row.get('fill_id'))}"
        )

    print()
    print("USDRUB_SOURCE_CODE_HITS")
    for hit in code_hits[:200]:
        print(
            "USDRUB_SOURCE_CODE_HIT "
            f"file={hit['file']} "
            f"line={hit['line']} "
            f"pattern={hit['pattern']} "
            f"text={hit['text']}"
        )

    runtime_match = sum(
        1 for r in runtime_rows
        if r.get("symbol") == TARGET_SYMBOL and r.get("strategy") == TARGET_STRATEGY
    )

    trade_match = sum(int(r.get("trades") or 0) for r in trade_rows)
    code_hit_count = len(code_hits)

    print()
    print("USDRUB_SOURCE_ROUTE_AUDIT_SUMMARY")
    print(f"runtime_rows={len(runtime_rows)}")
    print(f"runtime_exact_match={runtime_match}")
    print(f"trade_rows={len(trade_rows)}")
    print(f"trades_today={trade_match}")
    print(f"code_hits={code_hit_count}")
    print("db_update=0")
    print("execution_changes_required=0")
    print("runtime_changes_required=0")

    if runtime_match == 0 and trade_match > 0:
        print("VERDICT=USDRUB_REGIME_SOURCE_NOT_RUNTIME_UNIVERSE")
    elif runtime_match > 0 and trade_match > 0:
        print("VERDICT=USDRUB_REGIME_SOURCE_RUNTIME_UNIVERSE")
    elif trade_match == 0:
        print("VERDICT=USDRUB_REGIME_NO_TODAY_TRADES")
    else:
        print("VERDICT=USDRUB_REGIME_SOURCE_REVIEW_REQUIRED")

    print("USDRUB_REGIME_SOURCE_ROUTE_AUDIT_V1_OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
