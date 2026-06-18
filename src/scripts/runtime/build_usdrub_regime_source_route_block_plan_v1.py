#!/usr/bin/env python3
from __future__ import annotations

import os
from pathlib import Path
from typing import Any

import psycopg2
import psycopg2.extras


# Русский комментарий:
# USDRUB_REGIME_SOURCE_ROUTE_BLOCK_PLAN_V1
# Только dry-run. Ничего не меняет.
# Цель: определить фактический маршрут USDRUB_REGIME и предложить безопасную точку блокировки.


TARGET_SYMBOL = "USDRUBF@RTSX"
TARGET_STRATEGY = "USDRUB_REGIME"

ENV_KEYS = [
    "ENABLE_USDRUBF_PAPER_ACCUMULATION_BYPASS_V1",
    "ENABLE_USDRUB_REGIME",
    "ENABLE_USDRUBF",
    "RUNTIME_ALLOW",
    "EXECUTION_ENABLED",
    "REAL_TRADING_ENABLED",
]

FILES_TO_CHECK = [
    "src/finam_core/strategy/symbol_strategy_map.py",
    "src/finam_core/pipelines/paper_pipeline.py",
    "src/finam_core/strategy/strategy_factory.py",
    "src/finam_core/strategy/dynamic_strategy_resolver.py",
    "src/finam_core/strategy/fx/usdrub_regime_strategy.py",
]


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
  and symbol = %s
  and strategy = %s
group by symbol, strategy, timeframe, continuous_symbol, trade_source, origin
order by trades desc;
"""


RUNTIME_ACTIVE_SQL = """
select *
from runtime_active_universe
where symbol = %s
   or strategy = %s
   or symbol ilike '%%USDRUB%%'
   or strategy ilike '%%USDRUB%%'
order by symbol, strategy, timeframe nulls last;
"""


RUNTIME_SELECTION_SQL = """
select *
from runtime_strategy_selection
where symbol = %s
   or strategy = %s
   or symbol ilike '%%USDRUB%%'
   or strategy ilike '%%USDRUB%%'
order by symbol, strategy, mode nulls last
limit 50;
"""


def fmt(value: Any) -> str:
    if value is None:
        return "NULL"
    return str(value)


def table_exists(cur: Any, table: str) -> bool:
    cur.execute(
        """
        select exists (
            select 1
            from information_schema.tables
            where table_name = %s
        ) as exists
        """,
        (table,),
    )
    row = cur.fetchone() or {}
    return bool(row.get("exists"))


def scan_file(path: Path) -> list[dict[str, Any]]:
    patterns = [
        TARGET_SYMBOL,
        TARGET_STRATEGY,
        "USDRUB_CONT",
        "ENABLE_USDRUBF_PAPER_ACCUMULATION_BYPASS_V1",
        "_strategy_name_for_symbol",
        "SYMBOL_STRATEGY_MAP",
        "DEFAULT_STRATEGY",
        "USDRUBF_PAPER_ACCUMULATION_BYPASS",
    ]

    rows: list[dict[str, Any]] = []
    if not path.exists():
        return rows

    text = path.read_text(encoding="utf-8", errors="ignore")
    for i, line in enumerate(text.splitlines(), start=1):
        for pattern in patterns:
            if pattern in line:
                rows.append(
                    {
                        "file": str(path),
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

    print("=== USDRUB REGIME SOURCE ROUTE BLOCK PLAN V1 ===")
    print("mode=dry_run")
    print("runtime_allow=0")
    print("execution_enabled=0")
    print("real_trading_enabled=0")
    print("db_update=0")
    print(f"target_symbol={TARGET_SYMBOL}")
    print(f"target_strategy={TARGET_STRATEGY}")
    print()

    print("USDRUB_BLOCK_PLAN_ENV")
    for key in ENV_KEYS:
        print(f"USDRUB_BLOCK_PLAN_ENV_ROW key={key} value={fmt(os.getenv(key))}")

    with psycopg2.connect(dsn) as conn:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute(TODAY_TRADES_SQL, (TARGET_SYMBOL, TARGET_STRATEGY))
            trade_rows = cur.fetchall()

            cur.execute(RUNTIME_ACTIVE_SQL, (TARGET_SYMBOL, TARGET_STRATEGY))
            runtime_active_rows = cur.fetchall()

            if table_exists(cur, "runtime_strategy_selection"):
                cur.execute(RUNTIME_SELECTION_SQL, (TARGET_SYMBOL, TARGET_STRATEGY))
                runtime_selection_rows = cur.fetchall()
            else:
                runtime_selection_rows = []

    print()
    print("USDRUB_BLOCK_PLAN_TRADE_ROWS")
    for row in trade_rows:
        print(
            "USDRUB_BLOCK_PLAN_TRADE_ROW "
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
    print("USDRUB_BLOCK_PLAN_RUNTIME_ACTIVE_ROWS")
    for row in runtime_active_rows:
        print(
            "USDRUB_BLOCK_PLAN_RUNTIME_ACTIVE_ROW "
            f"symbol={fmt(row.get('symbol'))} "
            f"strategy={fmt(row.get('strategy'))} "
            f"timeframe={fmt(row.get('timeframe'))} "
            f"is_enabled={fmt(row.get('is_enabled'))} "
            f"source={fmt(row.get('source'))} "
            f"disable_reason={fmt(row.get('disable_reason'))}"
        )

    print()
    print("USDRUB_BLOCK_PLAN_RUNTIME_SELECTION_ROWS")
    for row in runtime_selection_rows:
        print(
            "USDRUB_BLOCK_PLAN_RUNTIME_SELECTION_ROW "
            f"symbol={fmt(row.get('symbol'))} "
            f"strategy={fmt(row.get('strategy'))} "
            f"mode={fmt(row.get('mode'))} "
            f"enabled={fmt(row.get('enabled'))} "
            f"reason={fmt(row.get('reason'))}"
        )

    repo = Path.cwd()
    hits: list[dict[str, Any]] = []
    for raw in FILES_TO_CHECK:
        hits.extend(scan_file(repo / raw))

    print()
    print("USDRUB_BLOCK_PLAN_CODE_HITS")
    for hit in hits:
        print(
            "USDRUB_BLOCK_PLAN_CODE_HIT "
            f"file={hit['file']} "
            f"line={hit['line']} "
            f"pattern={hit['pattern']} "
            f"text={hit['text']}"
        )

    trades_today = sum(int(row.get("trades") or 0) for row in trade_rows)
    runtime_active_match = sum(
        1
        for row in runtime_active_rows
        if row.get("symbol") == TARGET_SYMBOL and row.get("strategy") == TARGET_STRATEGY
    )
    runtime_selection_match = sum(
        1
        for row in runtime_selection_rows
        if row.get("symbol") == TARGET_SYMBOL and row.get("strategy") == TARGET_STRATEGY
    )

    symbol_map_hit = any(
        hit["file"].endswith("symbol_strategy_map.py")
        and hit["pattern"] in (TARGET_SYMBOL, TARGET_STRATEGY)
        for hit in hits
    )

    bypass_hit = any(
        hit["pattern"] == "ENABLE_USDRUBF_PAPER_ACCUMULATION_BYPASS_V1"
        for hit in hits
    )

    print()
    print("USDRUB_BLOCK_PLAN_RECOMMENDATION")
    print("recommended_primary_patch=paper_pipeline_usdrub_fee_drag_block")
    print("recommended_secondary_patch=symbol_strategy_map_research_only_guard")
    print("recommended_disable_env=ENABLE_USDRUBF_PAPER_ACCUMULATION_BYPASS_V1=0")
    print("recommended_do_not_remove_history=1")
    print("recommended_real_trading_enabled=0")
    print("recommended_execution_enabled=0")
    print("recommended_db_update=0")
    print("recommended_patch_mode=guard_before_signal_or_intent")
    print("recommended_reason=fee_drag_dominates_no_runtime_universe_control")

    print()
    print("USDRUB_SOURCE_ROUTE_BLOCK_PLAN_SUMMARY")
    print(f"trades_today={trades_today}")
    print(f"runtime_active_match={runtime_active_match}")
    print(f"runtime_selection_match={runtime_selection_match}")
    print(f"symbol_strategy_map_hit={1 if symbol_map_hit else 0}")
    print(f"paper_bypass_hit={1 if bypass_hit else 0}")
    print(f"code_hits={len(hits)}")
    print("db_update=0")
    print("execution_changes_required=0")
    print("runtime_changes_required=1")

    if trades_today > 0 and runtime_active_match == 0 and symbol_map_hit:
        print("VERDICT=USDRUB_ROUTE_BLOCK_REQUIRED_LEGACY_SYMBOL_MAP")
    elif trades_today > 0 and runtime_selection_match > 0:
        print("VERDICT=USDRUB_ROUTE_BLOCK_REQUIRED_RUNTIME_SELECTION")
    elif trades_today > 0:
        print("VERDICT=USDRUB_ROUTE_BLOCK_REQUIRED_PIPELINE_FALLBACK")
    else:
        print("VERDICT=USDRUB_ROUTE_NO_TODAY_TRADES")

    print("USDRUB_REGIME_SOURCE_ROUTE_BLOCK_PLAN_V1_OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
