#!/usr/bin/env python3
from __future__ import annotations

import os
from typing import Any

import psycopg2
import psycopg2.extras


# Русский комментарий:
# USDRUB_REGIME_QUARANTINE_APPLY_PLAN_V1
# Только dry-run. Никаких изменений runtime_active_universe.
# Цель: показать, какие runtime-строки будут отключены из-за fee drag.


TARGET_SYMBOL = "USDRUBF@RTSX"
TARGET_STRATEGY = "USDRUB_REGIME"


RUNTIME_SCHEMA_SQL = """
select column_name
from information_schema.columns
where table_name = 'runtime_active_universe'
order by ordinal_position;
"""


RUNTIME_ROWS_SQL = """
select *
from runtime_active_universe
where symbol = %s
   or strategy = %s
order by symbol, strategy, timeframe nulls last;
"""


TODAY_METRICS_SQL = """
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


TODAY_CONTEXT_SQL = """
select
    count(*) as unknown_rows
from trades
where created_at::date = current_date
  and symbol = %s
  and (
        coalesce(strategy, '') = ''
     or strategy in ('UNKNOWN', 'UNKNOWN_STRATEGY')
     or coalesce(timeframe, '') = ''
     or timeframe in ('UNKNOWN', 'UNKNOWN_TIMEFRAME')
     or coalesce(continuous_symbol, '') = ''
  );
"""


def fmt(value: Any) -> str:
    if value is None:
        return "NULL"
    return str(value)


def main() -> int:
    dsn = os.getenv("DATABASE_URL")
    if not dsn:
        raise SystemExit("DATABASE_URL is required")

    print("=== USDRUB REGIME QUARANTINE APPLY PLAN V1 ===")
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
            cur.execute(RUNTIME_SCHEMA_SQL)
            columns = [r["column_name"] for r in cur.fetchall()]

            cur.execute(RUNTIME_ROWS_SQL, (TARGET_SYMBOL, TARGET_STRATEGY))
            runtime_rows = cur.fetchall()

            cur.execute(TODAY_METRICS_SQL, (TARGET_SYMBOL, TARGET_STRATEGY))
            metrics = cur.fetchone() or {}

            cur.execute(TODAY_CONTEXT_SQL, (TARGET_SYMBOL,))
            context = cur.fetchone() or {}

    has_is_enabled = "is_enabled" in columns
    has_disabled_at = "disabled_at" in columns
    has_disable_reason = "disable_reason" in columns
    has_source = "source" in columns
    has_raw_json = "raw_json" in columns

    print("USDRUB_QUARANTINE_RUNTIME_SCHEMA")
    print(f"columns={','.join(columns)}")
    print(f"has_is_enabled={1 if has_is_enabled else 0}")
    print(f"has_disabled_at={1 if has_disabled_at else 0}")
    print(f"has_disable_reason={1 if has_disable_reason else 0}")
    print(f"has_source={1 if has_source else 0}")
    print(f"has_raw_json={1 if has_raw_json else 0}")
    print()

    print("USDRUB_QUARANTINE_TODAY_METRICS")
    print(f"trades={fmt(metrics.get('trades'))}")
    print(f"buy_trades={fmt(metrics.get('buy_trades'))}")
    print(f"sell_trades={fmt(metrics.get('sell_trades'))}")
    print(f"first_trade={fmt(metrics.get('first_trade'))}")
    print(f"last_trade={fmt(metrics.get('last_trade'))}")
    print(f"unknown_rows={fmt(context.get('unknown_rows'))}")
    print()

    print("USDRUB_QUARANTINE_PLAN_ROWS")
    planned_changes = 0
    runtime_match = 0

    for row in runtime_rows:
        symbol = row.get("symbol")
        strategy = row.get("strategy")
        timeframe = row.get("timeframe")
        is_enabled = row.get("is_enabled")

        exact_match = symbol == TARGET_SYMBOL and strategy == TARGET_STRATEGY
        if exact_match:
            runtime_match += 1

        should_disable = exact_match and str(is_enabled).lower() in ("true", "t", "1", "yes")
        if should_disable:
            planned_changes += 1

        action = "DISABLE_RUNTIME_SET_RESEARCH_ONLY" if should_disable else "NO_CHANGE"
        reason = "fee_drag_dominates" if exact_match else "not_exact_target"

        print(
            "USDRUB_QUARANTINE_PLAN_ROW "
            f"symbol={fmt(symbol)} "
            f"strategy={fmt(strategy)} "
            f"timeframe={fmt(timeframe)} "
            f"is_enabled={fmt(is_enabled)} "
            f"exact_match={1 if exact_match else 0} "
            f"planned_action={action} "
            f"reason={reason}"
        )

    print()
    print("USDRUB_QUARANTINE_APPLY_PLAN_SUMMARY")
    print(f"runtime_rows={len(runtime_rows)}")
    print(f"runtime_match={runtime_match}")
    print(f"planned_changes={planned_changes}")
    print("db_update=0")
    print("execution_changes_required=0")
    print(f"runtime_changes_required={1 if planned_changes > 0 else 0}")
    print("recommended_action=QUARANTINE_RUNTIME")
    print("recommended_runtime_enabled=0")
    print("recommended_research_only=1")
    print("recommended_max_trades_per_day=5")
    print("recommended_cooldown_after_trade_sec=900")
    print("recommended_min_hold_sec=600")
    print("recommended_min_expected_gross_move=0.220260")
    print("recommended_entry_mode=IMPULSE_ONLY")
    print("recommended_disable_scalping=1")

    if runtime_match == 0:
        print("VERDICT=USDRUB_REGIME_QUARANTINE_PLAN_NO_RUNTIME_MATCH")
    elif planned_changes > 0:
        print("VERDICT=USDRUB_REGIME_QUARANTINE_PLAN_READY")
    else:
        print("VERDICT=USDRUB_REGIME_ALREADY_DISABLED_OR_NO_CHANGE")

    print("USDRUB_REGIME_QUARANTINE_APPLY_PLAN_V1_OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
