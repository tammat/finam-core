#!/usr/bin/env python3
from __future__ import annotations

import os
from typing import Any

import psycopg2
import psycopg2.extras


# Русский комментарий:
# FULL_RUNTIME_STRATEGY_PAUSE_APPLY_DRY_RUN_V1
# Только dry-run. Никаких UPDATE.
# Показывает точные runtime_active_universe строки, которые будут отключены.


TARGET_STRATEGY = "NG_CONSERVATIVE_BREAKOUT_M1"
TARGET_SYMBOLS = ("NGF6@RTSX", "NGM6@RTSX")


SQL = """
select
    symbol,
    strategy,
    timeframe,
    is_enabled,
    source,
    score,
    priority,
    updated_at,
    disabled_at,
    disable_reason
from runtime_active_universe
where symbol = any(%s)
  and strategy = %s
order by symbol, timeframe;
"""


def fmt(v: Any) -> str:
    if v is None:
        return "NULL"
    return str(v)


def main() -> int:
    dsn = os.getenv("DATABASE_URL")
    if not dsn:
        raise SystemExit("DATABASE_URL is required")

    print("=== FULL RUNTIME STRATEGY PAUSE APPLY DRY RUN V1 ===")
    print("mode=dry_run")
    print("runtime_allow=0")
    print("execution_enabled=0")
    print("real_trading_enabled=0")
    print("db_update=0")
    print("target_strategy=NG_CONSERVATIVE_BREAKOUT_M1")
    print("target_symbols=NGF6@RTSX,NGM6@RTSX")
    print()

    with psycopg2.connect(dsn) as conn:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute(SQL, (list(TARGET_SYMBOLS), TARGET_STRATEGY))
            rows = cur.fetchall()

    planned_updates = 0

    print("FULL_RUNTIME_PAUSE_APPLY_DRY_RUN_ROWS")
    for row in rows:
        is_enabled = str(row.get("is_enabled")).lower() in {"true", "t", "1"}
        planned_action = "DISABLE_RUNTIME_SET_RESEARCH_ONLY" if is_enabled else "NO_CHANGE_ALREADY_DISABLED"

        if is_enabled:
            planned_updates += 1

        print(
            "FULL_RUNTIME_PAUSE_APPLY_DRY_RUN_ROW "
            f"symbol={fmt(row.get('symbol'))} "
            f"strategy={fmt(row.get('strategy'))} "
            f"timeframe={fmt(row.get('timeframe'))} "
            f"is_enabled={fmt(row.get('is_enabled'))} "
            f"source={fmt(row.get('source'))} "
            f"score={fmt(row.get('score'))} "
            f"priority={fmt(row.get('priority'))} "
            f"planned_action={planned_action} "
            "reason=ng_candidate_rejected_negative_sample"
        )

    print()
    print("FULL_RUNTIME_PAUSE_APPLY_DRY_RUN_SQL")
    print("update runtime_active_universe")
    print("set is_enabled=false, disabled_at=now(), disable_reason='ng_candidate_rejected_negative_sample'")
    print("where symbol in ('NGF6@RTSX','NGM6@RTSX')")
    print("  and strategy='NG_CONSERVATIVE_BREAKOUT_M1'")
    print("  and is_enabled=true;")

    print()
    print("FULL_RUNTIME_PAUSE_APPLY_DRY_RUN_SUMMARY")
    print(f"rows_total={len(rows)}")
    print(f"planned_updates={planned_updates}")
    print("db_update=0")
    print(f"runtime_changes_required={1 if planned_updates > 0 else 0}")
    print("execution_changes_required=0")
    print("recommended_apply_requires_manual_confirmation=1")

    if planned_updates > 0:
        print("VERDICT=FULL_RUNTIME_STRATEGY_PAUSE_APPLY_DRY_RUN_READY")
    else:
        print("VERDICT=FULL_RUNTIME_STRATEGY_PAUSE_APPLY_DRY_RUN_NO_CHANGE_REQUIRED")

    print("FULL_RUNTIME_STRATEGY_PAUSE_APPLY_DRY_RUN_V1_OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
