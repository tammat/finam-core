#!/usr/bin/env python3
from __future__ import annotations

import os
from pathlib import Path
from typing import Any

import psycopg2
import psycopg2.extras


# Русский комментарий:
# USDRUB_REGIME_RUNTIME_BLOCK_GUARD_PLAN_V1
# Только dry-run. Проверяет, где безопасно вставить guard в paper_pipeline.py.
# Ничего не меняет в БД, runtime, execution и real trading.


TARGET_SYMBOL = "USDRUBF@RTSX"
TARGET_STRATEGY = "USDRUB_REGIME"

PIPELINE_FILE = Path("src/finam_core/pipelines/paper_pipeline.py")


RUNTIME_SELECTION_SQL = """
select
    symbol,
    strategy,
    mode,
    enabled,
    reason
from runtime_strategy_selection
where symbol = %s
  and strategy = %s
order by updated_at desc nulls last
limit 10;
"""


TODAY_TRADES_SQL = """
select
    count(*) as trades,
    count(*) filter (where side = 'BUY') as buy_trades,
    count(*) filter (where side = 'SELL') as sell_trades,
    min(created_at) as first_trade,
    max(created_at) as last_trade
from trades
where created_at::date = current_date
  and symbol = %s
  and strategy = %s;
"""


def fmt(value: Any) -> str:
    if value is None:
        return "NULL"
    return str(value)


def find_pipeline_guard_points() -> list[dict[str, Any]]:
    if not PIPELINE_FILE.exists():
        return []

    lines = PIPELINE_FILE.read_text(encoding="utf-8", errors="ignore").splitlines()
    points: list[dict[str, Any]] = []

    patterns = [
        "_strategy_name_for_symbol(",
        "_runtime_strategy_name_for_symbol(",
        "StrategyFactory",
        "create_intent",
        "execution_intent",
        "position_intent",
        "FillEvent",
        "log_trade",
        "USDRUBF@RTSX",
        "USDRUBF_PAPER_ACCUMULATION_BYPASS",
    ]

    for i, line in enumerate(lines, start=1):
        for pattern in patterns:
            if pattern in line:
                points.append(
                    {
                        "line": i,
                        "pattern": pattern,
                        "text": line.strip()[:240],
                    }
                )

    return points


def main() -> int:
    dsn = os.getenv("DATABASE_URL")
    if not dsn:
        raise SystemExit("DATABASE_URL is required")

    print("=== USDRUB REGIME RUNTIME BLOCK GUARD PLAN V1 ===")
    print("mode=dry_run")
    print("runtime_allow=0")
    print("execution_enabled=0")
    print("real_trading_enabled=0")
    print("db_update=0")
    print(f"target_symbol={TARGET_SYMBOL}")
    print(f"target_strategy={TARGET_STRATEGY}")
    print()

    with psycopg2.connect(dsn) as conn:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute(RUNTIME_SELECTION_SQL, (TARGET_SYMBOL, TARGET_STRATEGY))
            selection_rows = cur.fetchall()

            cur.execute(TODAY_TRADES_SQL, (TARGET_SYMBOL, TARGET_STRATEGY))
            today = cur.fetchone() or {}

    points = find_pipeline_guard_points()

    print("USDRUB_RUNTIME_BLOCK_SELECTION_ROWS")
    blocked_rows = 0
    for row in selection_rows:
        enabled = row.get("enabled")
        mode = str(row.get("mode") or "")
        is_blocked = (mode.upper() == "BLOCKED") or (str(enabled).lower() in ("false", "f", "0"))
        if is_blocked:
            blocked_rows += 1

        print(
            "USDRUB_RUNTIME_BLOCK_SELECTION_ROW "
            f"symbol={fmt(row.get('symbol'))} "
            f"strategy={fmt(row.get('strategy'))} "
            f"mode={fmt(row.get('mode'))} "
            f"enabled={fmt(row.get('enabled'))} "
            f"reason={fmt(row.get('reason'))} "
            f"is_blocked={1 if is_blocked else 0}"
        )

    print()
    print("USDRUB_RUNTIME_BLOCK_TODAY")
    print(f"trades={fmt(today.get('trades'))}")
    print(f"buy_trades={fmt(today.get('buy_trades'))}")
    print(f"sell_trades={fmt(today.get('sell_trades'))}")
    print(f"first_trade={fmt(today.get('first_trade'))}")
    print(f"last_trade={fmt(today.get('last_trade'))}")

    print()
    print("USDRUB_RUNTIME_BLOCK_GUARD_POINTS")
    for point in points[:120]:
        print(
            "USDRUB_RUNTIME_BLOCK_GUARD_POINT "
            f"line={point['line']} "
            f"pattern={point['pattern']} "
            f"text={point['text']}"
        )

    print()
    print("USDRUB_RUNTIME_BLOCK_RECOMMENDATION")
    print("recommended_patch_file=src/finam_core/pipelines/paper_pipeline.py")
    print("recommended_guard_function=_is_runtime_strategy_blocked_v1")
    print("recommended_guard_scope=paper_runtime_only")
    print("recommended_block_symbol=USDRUBF@RTSX")
    print("recommended_block_strategy=USDRUB_REGIME")
    print("recommended_block_before=signal_intent_fill")
    print("recommended_preserve_research_replay=1")
    print("recommended_preserve_strategy_map=1")
    print("recommended_preserve_real_execution=1")
    print("recommended_db_update=0")

    trades_today = int(today.get("trades") or 0)

    print()
    print("USDRUB_RUNTIME_BLOCK_GUARD_PLAN_SUMMARY")
    print(f"runtime_selection_rows={len(selection_rows)}")
    print(f"blocked_selection_rows={blocked_rows}")
    print(f"trades_today={trades_today}")
    print(f"pipeline_guard_points={len(points)}")
    print("db_update=0")
    print("execution_changes_required=0")
    print("runtime_changes_required=1")

    if blocked_rows > 0 and trades_today > 0:
        print("VERDICT=USDRUB_RUNTIME_BLOCK_GUARD_REQUIRED")
    elif blocked_rows > 0 and trades_today == 0:
        print("VERDICT=USDRUB_RUNTIME_BLOCK_ALREADY_EFFECTIVE_OR_NO_TRADES")
    else:
        print("VERDICT=USDRUB_RUNTIME_BLOCK_SELECTION_NOT_BLOCKED")

    print("USDRUB_REGIME_RUNTIME_BLOCK_GUARD_PLAN_V1_OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
