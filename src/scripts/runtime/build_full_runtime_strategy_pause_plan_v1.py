#!/usr/bin/env python3
from __future__ import annotations

import os
from typing import Any

import psycopg2
import psycopg2.extras


# Русский комментарий:
# FULL_RUNTIME_STRATEGY_PAUSE_PLAN_V1
# Dry-run план остановки активных runtime/paper стратегий без подтверждённого edge.
# Ничего не меняет в БД, runtime, execution и real trading.


TODAY_EDGE_SQL = """
select
    symbol,
    strategy,
    timeframe,
    continuous_symbol,
    count(*) as trades,
    min(created_at) as first_trade,
    max(created_at) as last_trade
from trades
where created_at::date = current_date
  and coalesce(is_invalid, false) = false
group by symbol, strategy, timeframe, continuous_symbol
order by trades desc, symbol, strategy, timeframe;
"""


RUNTIME_ACTIVE_SQL = """
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
order by is_enabled desc, priority desc nulls last, score desc nulls last, updated_at desc nulls last;
"""


RUNTIME_SELECTION_SQL = """
select
    symbol,
    strategy,
    mode,
    enabled,
    reason
from runtime_strategy_selection
where symbol in ('USDRUBF@RTSX', 'NGM6@RTSX', 'NGN6@RTSX', 'BRN6@RTSX')
   or strategy in ('USDRUB_REGIME', 'NG_CONSERVATIVE_BREAKOUT_M1', 'BR_CONSERVATIVE_BREAKOUT')
order by symbol, strategy, mode;
"""


CONTEXT_SQL = """
select
    count(*) as unknown_rows
from trades
where created_at::date = current_date
  and (
        coalesce(strategy, '') = ''
     or strategy in ('UNKNOWN', 'UNKNOWN_STRATEGY')
     or coalesce(timeframe, '') = ''
     or timeframe in ('UNKNOWN', 'UNKNOWN_TIMEFRAME')
     or coalesce(continuous_symbol, '') = ''
  );
"""


def fmt(v: Any) -> str:
    if v is None:
        return "NULL"
    return str(v)


def classify_runtime_row(row: dict[str, Any]) -> tuple[str, str, int]:
    symbol = str(row.get("symbol") or "")
    strategy = str(row.get("strategy") or "")
    source = str(row.get("source") or "")

    if symbol == "USDRUBF@RTSX" or strategy == "USDRUB_REGIME":
        return "KEEP_BLOCKED", "usdrub_fee_drag_confirmed_and_blocked", 0

    if strategy in {"NG_CONSERVATIVE_BREAKOUT_M1", "NG_CONSERVATIVE_BREAKOUT"} or symbol.startswith("NG"):
        return "PAUSE_RUNTIME", "ng_candidate_rejected_negative_sample", 1

    if strategy == "BR_CONSERVATIVE_BREAKOUT" or symbol.startswith("BR"):
        return "KEEP_RESEARCH_ONLY", "br_insufficient_data", 0

    if strategy == "VOLATILITY_BREAKOUT_EQUITY" and symbol.endswith("@MISX"):
        return "KEEP_SHADOW_OBSERVATION", "equity_shadow_runtime_observation_only", 0

    if "runtime_universe_allocator" in source:
        return "KEEP_SHADOW_OBSERVATION", "allocator_shadow_observation", 0

    return "REVIEW_REQUIRED", "unclassified_runtime_row", 0


def main() -> int:
    dsn = os.getenv("DATABASE_URL")
    if not dsn:
        raise SystemExit("DATABASE_URL is required")

    print("=== FULL RUNTIME STRATEGY PAUSE PLAN V1 ===")
    print("mode=dry_run")
    print("runtime_allow=0")
    print("execution_enabled=0")
    print("real_trading_enabled=0")
    print("db_update=0")
    print()

    with psycopg2.connect(dsn) as conn:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute(TODAY_EDGE_SQL)
            today_rows = cur.fetchall()

            cur.execute(RUNTIME_ACTIVE_SQL)
            runtime_rows = cur.fetchall()

            cur.execute(RUNTIME_SELECTION_SQL)
            selection_rows = cur.fetchall()

            cur.execute(CONTEXT_SQL)
            context_row = cur.fetchone() or {}

    print("FULL_RUNTIME_PAUSE_TODAY_ROWS")
    for row in today_rows:
        print(
            "FULL_RUNTIME_PAUSE_TODAY_ROW "
            f"symbol={fmt(row.get('symbol'))} "
            f"strategy={fmt(row.get('strategy'))} "
            f"timeframe={fmt(row.get('timeframe'))} "
            f"continuous_symbol={fmt(row.get('continuous_symbol'))} "
            f"trades={fmt(row.get('trades'))} "
            f"first_trade={fmt(row.get('first_trade'))} "
            f"last_trade={fmt(row.get('last_trade'))}"
        )

    print()
    print("FULL_RUNTIME_PAUSE_SELECTION_ROWS")
    for row in selection_rows:
        print(
            "FULL_RUNTIME_PAUSE_SELECTION_ROW "
            f"symbol={fmt(row.get('symbol'))} "
            f"strategy={fmt(row.get('strategy'))} "
            f"mode={fmt(row.get('mode'))} "
            f"enabled={fmt(row.get('enabled'))} "
            f"reason={fmt(row.get('reason'))}"
        )

    print()
    print("FULL_RUNTIME_PAUSE_PLAN_ROWS")

    pause_candidates = 0
    keep_shadow = 0
    keep_blocked = 0
    review_required = 0

    for row in runtime_rows:
        action, reason, runtime_change = classify_runtime_row(row)

        if action == "PAUSE_RUNTIME":
            pause_candidates += 1
        elif action == "KEEP_SHADOW_OBSERVATION":
            keep_shadow += 1
        elif action == "KEEP_BLOCKED":
            keep_blocked += 1
        elif action == "REVIEW_REQUIRED":
            review_required += 1

        print(
            "FULL_RUNTIME_PAUSE_PLAN_ROW "
            f"symbol={fmt(row.get('symbol'))} "
            f"strategy={fmt(row.get('strategy'))} "
            f"timeframe={fmt(row.get('timeframe'))} "
            f"is_enabled={fmt(row.get('is_enabled'))} "
            f"source={fmt(row.get('source'))} "
            f"score={fmt(row.get('score'))} "
            f"priority={fmt(row.get('priority'))} "
            f"planned_action={action} "
            f"reason={reason} "
            f"runtime_change_required={runtime_change}"
        )

    unknown_rows = int(context_row.get("unknown_rows") or 0)
    today_trades_total = sum(int(r.get("trades") or 0) for r in today_rows)

    print()
    print("FULL_RUNTIME_STRATEGY_PAUSE_PLAN_SUMMARY")
    print(f"today_trades_total={today_trades_total}")
    print(f"today_unknown_rows={unknown_rows}")
    print(f"runtime_rows={len(runtime_rows)}")
    print(f"pause_candidates={pause_candidates}")
    print(f"keep_shadow_observation={keep_shadow}")
    print(f"keep_blocked={keep_blocked}")
    print(f"review_required={review_required}")
    print("db_update=0")
    print("execution_changes_required=0")
    print(f"runtime_changes_required={1 if pause_candidates > 0 else 0}")
    print("recommended_real_trading_enabled=0")
    print("recommended_execution_enabled=0")
    print("recommended_runtime_allow=0")
    print("recommended_next_research_mode=historical_replay_only")

    if unknown_rows > 0:
        print("VERDICT=FULL_RUNTIME_PAUSE_CONTEXT_DIRTY")
    elif pause_candidates > 0:
        print("VERDICT=FULL_RUNTIME_STRATEGY_PAUSE_PLAN_READY")
    elif review_required > 0:
        print("VERDICT=FULL_RUNTIME_STRATEGY_PAUSE_REVIEW_REQUIRED")
    else:
        print("VERDICT=FULL_RUNTIME_STRATEGY_PAUSE_NO_RUNTIME_CHANGE_REQUIRED")

    print("FULL_RUNTIME_STRATEGY_PAUSE_PLAN_V1_OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
