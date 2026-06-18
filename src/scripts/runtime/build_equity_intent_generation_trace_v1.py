#!/usr/bin/env python3
from __future__ import annotations

import os
from typing import Any

import psycopg2
import psycopg2.extras


# Русский комментарий:
# EQUITY_INTENT_GENERATION_TRACE_V1 — read-only trace по SBER@MISX.
# Цель: найти, создаются ли signals / signal_features / quality audit /
# runtime guard blocks / execution_intents / position_intents.
# Ничего не меняет в БД, runtime, systemd и execution.


# EQUITY_INTENT_GENERATION_TRACE_V1_1_SCHEMA_SAFE
# EQUITY_INTENT_GENERATION_TRACE_V1_2_PARAM_SAFE
TABLES_SQL = """
SELECT table_name
FROM information_schema.tables
WHERE table_schema = 'public'
  AND table_name = ANY(%s)
ORDER BY table_name;
"""


COLUMNS_SQL = """
SELECT table_name, column_name
FROM information_schema.columns
WHERE table_schema = 'public'
  AND table_name = ANY(%s)
ORDER BY table_name, ordinal_position;
"""


def norm(value: Any) -> str:
    if value is None:
        return ""
    return str(value).strip()


def table_exists(existing: set[str], table: str) -> bool:
    return table in existing


def fetch_rows(cur: Any, sql: str, params: tuple[Any, ...]) -> list[dict[str, Any]]:
    cur.execute(sql, params)
    return [dict(r) for r in cur.fetchall()]


def safe_select(
    conn: Any,
    cur: Any,
    existing: set[str],
    table: str,
    sql: str,
    params: tuple[Any, ...],
) -> tuple[str, list[dict[str, Any]]]:
    if not table_exists(existing, table):
        return "TABLE_MISSING", []

    try:
        return "OK", fetch_rows(cur, sql, params)
    except Exception as exc:
        conn.rollback()
        return f"QUERY_FAILED:{type(exc).__name__}:{str(exc).replace(chr(10), ' ')}", []


def print_rows(prefix: str, rows: list[dict[str, Any]], fields: tuple[str, ...]) -> None:
    for row in rows:
        parts = []
        for field in fields:
            parts.append(f"{field}={norm(row.get(field)) or 'NULL'}")
        print(f"{prefix} " + " ".join(parts))

def select_expr(table_columns: dict[str, set[str]], table: str, column: str, alias: str | None = None) -> str:
    alias_name = alias or column
    if column in table_columns.get(table, set()):
        return f"{column}::text AS {alias_name}"
    return f"NULL::text AS {alias_name}"


def where_symbol_clause(table_columns: dict[str, set[str]], table: str) -> str:
    if "symbol" in table_columns.get(table, set()):
        return "symbol = %s"
    if "payload" in table_columns.get(table, set()):
        return "(payload::text ILIKE %s)"
    if "raw_json" in table_columns.get(table, set()):
        return "(raw_json::text ILIKE %s)"
    return "1 = 0"


def symbol_param(table_columns: dict[str, set[str]], table: str, symbol: str) -> str:
    if "symbol" in table_columns.get(table, set()):
        return symbol
    return f"%{symbol}%"


def time_column(table_columns: dict[str, set[str]], table: str) -> str:
    cols = table_columns.get(table, set())
    for candidate in ("created_at", "ts", "timestamp", "event_time", "updated_at"):
        if candidate in cols:
            return candidate
    return ""


def time_clause(table_columns: dict[str, set[str]], table: str) -> str:
    col = time_column(table_columns, table)
    if col:
        return f"{col} >= now() - (%s::text)::interval"
    return "1 = 1"


def build_generic_trace_sql(
    table_columns: dict[str, set[str]],
    table: str,
    desired: tuple[str, ...],
) -> tuple[str, tuple[str, ...], tuple[str, ...]]:
    cols = table_columns.get(table, set())
    selected = []
    output_fields = []

    for col in desired:
        selected.append(select_expr(table_columns, table, col))
        output_fields.append(col)

    if "created_at" not in desired:
        selected.append(select_expr(table_columns, table, "created_at"))
        output_fields.append("created_at")

    where_symbol = where_symbol_clause(table_columns, table)
    where_time = time_clause(table_columns, table)

    params_needed = []
    if "%s" in where_symbol:
        params_needed.append("symbol")
    if "%s" in where_time:
        params_needed.append("lookback")

    order_col = time_column(table_columns, table) or "1"

    sql = f"""
        SELECT
            {", ".join(selected)}
        FROM {table}
        WHERE {where_symbol}
          AND {where_time}
        ORDER BY {order_col} DESC
        LIMIT 20;
    """

    return sql, tuple(output_fields), tuple(params_needed)



def build_params(
    table_columns: dict[str, set[str]],
    table: str,
    symbol: str,
    lookback: str,
    params_needed: tuple[str, ...],
) -> tuple[Any, ...]:
    params: list[Any] = []
    for item in params_needed:
        if item == "symbol":
            params.append(symbol_param(table_columns, table, symbol))
        elif item == "lookback":
            params.append(lookback)
    return tuple(params)


def main() -> int:
    dsn = os.getenv("DATABASE_URL")
    if not dsn:
        raise SystemExit("DATABASE_URL is required")

    symbol = os.getenv("EQUITY_TRACE_SYMBOL", "SBER@MISX")
    lookback = os.getenv("EQUITY_TRACE_LOOKBACK", "24 hours")

    wanted_tables = [
        "signals",
        "signal_features",
        "signal_quality_audit_v1",
        "runtime_guard_pre_signal_block_audit_v1",
        "execution_intents",
        "position_intents",
        "execution_events",
        "risk_events",
        "event_store",
        "events",
    ]

    print("=== EQUITY INTENT GENERATION TRACE V1 ===")
    print("mode=read_only")
    print("runtime_allow=0")
    print("execution_enabled=0")
    print("real_trading_enabled=0")
    print("db_update=0")
    print(f"symbol={symbol}")
    print(f"lookback={lookback}")
    print()

    with psycopg2.connect(dsn) as conn:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute(TABLES_SQL, (wanted_tables,))
            existing = {r["table_name"] for r in cur.fetchall()}

            cur.execute(COLUMNS_SQL, (wanted_tables,))
            table_columns: dict[str, set[str]] = {}
            for r in cur.fetchall():
                table_columns.setdefault(r["table_name"], set()).add(r["column_name"])

            print("EQUITY_TRACE_TABLES")
            for table in wanted_tables:
                print(
                    "EQUITY_TRACE_TABLE "
                    f"table={table} "
                    f"exists={1 if table in existing else 0}"
                )

            trace_specs = {
                "signals": ("id", "symbol", "strategy", "timeframe", "direction", "side", "reason", "status", "created_at"),
                "signal_features": ("id", "signal_id", "symbol", "strategy", "timeframe", "created_at"),
                "signal_quality_audit_v1": ("id", "signal_id", "symbol", "strategy", "timeframe", "decision", "reason", "created_at"),
                "runtime_guard_pre_signal_block_audit_v1": ("id", "symbol", "strategy", "timeframe", "decision", "reason", "created_at"),
                "execution_intents": ("id", "symbol", "side", "qty", "order_type", "status", "strategy", "timeframe", "created_at"),
                "position_intents": ("id", "symbol", "side", "qty", "status", "strategy", "timeframe", "created_at"),
                "execution_events": ("id", "symbol", "event_type", "status", "created_at"),
                "risk_events": ("id", "symbol", "event_type", "decision", "reason", "created_at"),
                "events": ("id", "event_type", "symbol", "created_at"),
            }

            trace_results: dict[str, tuple[str, list[dict[str, Any]], tuple[str, ...]]] = {}

            for table, desired_fields in trace_specs.items():
                sql, fields, params_needed = build_generic_trace_sql(table_columns, table, desired_fields)
                params = build_params(table_columns, table, symbol, lookback, params_needed)
                status, rows = safe_select(
                    conn,
                    cur,
                    existing,
                    table,
                    sql,
                    params,
                )
                trace_results[table] = (status, rows, fields)

            signal_status, signal_rows, signal_fields = trace_results["signals"]
            feature_status, feature_rows, feature_fields = trace_results["signal_features"]
            quality_status, quality_rows, quality_fields = trace_results["signal_quality_audit_v1"]
            guard_status, guard_rows, guard_fields = trace_results["runtime_guard_pre_signal_block_audit_v1"]
            execution_intent_status, execution_intent_rows, execution_intent_fields = trace_results["execution_intents"]
            position_intent_status, position_intent_rows, position_intent_fields = trace_results["position_intents"]
            execution_event_status, execution_event_rows, execution_event_fields = trace_results["execution_events"]
            risk_status, risk_rows, risk_fields = trace_results["risk_events"]
            generic_event_status, generic_event_rows, generic_event_fields = trace_results["events"]

    sections = [
        ("signals", signal_status, signal_rows),
        ("signal_features", feature_status, feature_rows),
        ("signal_quality_audit_v1", quality_status, quality_rows),
        ("runtime_guard_pre_signal_block_audit_v1", guard_status, guard_rows),
        ("execution_intents", execution_intent_status, execution_intent_rows),
        ("position_intents", position_intent_status, position_intent_rows),
        ("execution_events", execution_event_status, execution_event_rows),
        ("risk_events", risk_status, risk_rows),
        ("events", generic_event_status, generic_event_rows),
    ]

    print()
    print("EQUITY_TRACE_SECTION_SUMMARY")
    for name, status, rows in sections:
        print(
            "EQUITY_TRACE_SECTION "
            f"name={name} "
            f"status={status} "
            f"rows={len(rows)}"
        )

    print()
    print("EQUITY_TRACE_SIGNALS")
    print_rows(
        "EQUITY_TRACE_SIGNAL_ROW",
        signal_rows,
        signal_fields,
    )

    print()
    print("EQUITY_TRACE_SIGNAL_FEATURES")
    print_rows(
        "EQUITY_TRACE_SIGNAL_FEATURE_ROW",
        feature_rows,
        feature_fields,
    )

    print()
    print("EQUITY_TRACE_SIGNAL_QUALITY")
    print_rows(
        "EQUITY_TRACE_SIGNAL_QUALITY_ROW",
        quality_rows,
        quality_fields,
    )

    print()
    print("EQUITY_TRACE_RUNTIME_GUARD")
    print_rows(
        "EQUITY_TRACE_RUNTIME_GUARD_ROW",
        guard_rows,
        guard_fields,
    )

    print()
    print("EQUITY_TRACE_EXECUTION_INTENTS")
    print_rows(
        "EQUITY_TRACE_EXECUTION_INTENT_ROW",
        execution_intent_rows,
        execution_intent_fields,
    )

    print()
    print("EQUITY_TRACE_POSITION_INTENTS")
    print_rows(
        "EQUITY_TRACE_POSITION_INTENT_ROW",
        position_intent_rows,
        position_intent_fields,
    )

    print()
    print("EQUITY_TRACE_EXECUTION_EVENTS")
    print_rows(
        "EQUITY_TRACE_EXECUTION_EVENT_ROW",
        execution_event_rows,
        execution_event_fields,
    )

    print()
    print("EQUITY_TRACE_RISK_EVENTS")
    print_rows(
        "EQUITY_TRACE_RISK_EVENT_ROW",
        risk_rows,
        risk_fields,
    )

    signals_count = len(signal_rows)
    features_count = len(feature_rows)
    quality_count = len(quality_rows)
    guard_count = len(guard_rows)

    expected_strategy = os.getenv("EQUITY_TRACE_STRATEGY", "VOLATILITY_BREAKOUT_EQUITY")
    expected_strategy_guard_count = sum(
        1 for row in guard_rows
        if norm(row.get("strategy")) == expected_strategy
    )
    other_strategy_guard_count = guard_count - expected_strategy_guard_count

    execution_intents_count = len(execution_intent_rows)
    position_intents_count = len(position_intent_rows)
    execution_events_count = len(execution_event_rows)
    risk_events_count = len(risk_rows)
    generic_events_count = len(generic_event_rows)

    if (
        signals_count == 0
        and features_count == 0
        and execution_intents_count == 0
        and position_intents_count == 0
        and expected_strategy_guard_count == 0
        and other_strategy_guard_count > 0
    ):
        diagnosis = "TRACE_EXISTS_ONLY_FOR_OTHER_EQUITY_STRATEGY"
        next_step = "verify_volatility_breakout_equity_wiring"
    elif signals_count == 0 and features_count == 0 and execution_intents_count == 0 and position_intents_count == 0:
        diagnosis = "NO_SIGNAL_OR_INTENT_TRACE"
        next_step = "verify_equity_strategy_invocation_in_pipeline"
    elif signals_count > 0 and execution_intents_count == 0 and position_intents_count == 0:
        diagnosis = "SIGNALS_EXIST_BUT_NO_INTENTS"
        next_step = "inspect_signal_router_or_risk_gate"
    elif execution_intents_count > 0 and execution_events_count == 0:
        diagnosis = "INTENTS_EXIST_BUT_NO_EXECUTION_EVENTS"
        next_step = "inspect_paper_execution_dispatch"
    elif execution_events_count > 0:
        diagnosis = "EXECUTION_EVENTS_EXIST_BUT_NO_TRADES"
        next_step = "inspect_fill_or_trade_persistence"
    else:
        diagnosis = "PARTIAL_TRACE_REVIEW_REQUIRED"
        next_step = "manual_trace_review"

    print()
    print("EQUITY_INTENT_GENERATION_TRACE_SUMMARY")
    print(f"symbol={symbol}")
    print(f"signals_count={signals_count}")
    print(f"signal_features_count={features_count}")
    print(f"signal_quality_count={quality_count}")
    print(f"runtime_guard_count={guard_count}")
    print(f"expected_strategy={expected_strategy}")
    print(f"expected_strategy_guard_count={expected_strategy_guard_count}")
    print(f"other_strategy_guard_count={other_strategy_guard_count}")
    print(f"execution_intents_count={execution_intents_count}")
    print(f"position_intents_count={position_intents_count}")
    print(f"execution_events_count={execution_events_count}")
    print(f"risk_events_count={risk_events_count}")
    print(f"generic_events_count={generic_events_count}")
    print(f"diagnosis={diagnosis}")
    print(f"next_step={next_step}")
    print("db_update=0")

    if diagnosis == "TRACE_EXISTS_ONLY_FOR_OTHER_EQUITY_STRATEGY":
        print("VERDICT=EQUITY_INTENT_GENERATION_TRACE_STRATEGY_WIRING_MISMATCH")
    elif diagnosis == "NO_SIGNAL_OR_INTENT_TRACE":
        print("VERDICT=EQUITY_INTENT_GENERATION_TRACE_NO_STRATEGY_TRACE")
    elif diagnosis == "SIGNALS_EXIST_BUT_NO_INTENTS":
        print("VERDICT=EQUITY_INTENT_GENERATION_TRACE_SIGNAL_ROUTING_BLOCK")
    elif diagnosis == "INTENTS_EXIST_BUT_NO_EXECUTION_EVENTS":
        print("VERDICT=EQUITY_INTENT_GENERATION_TRACE_EXECUTION_DISPATCH_BLOCK")
    elif diagnosis == "EXECUTION_EVENTS_EXIST_BUT_NO_TRADES":
        print("VERDICT=EQUITY_INTENT_GENERATION_TRACE_TRADE_PERSISTENCE_BLOCK")
    else:
        print("VERDICT=EQUITY_INTENT_GENERATION_TRACE_PARTIAL")

    print("EQUITY_INTENT_GENERATION_TRACE_V1_OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
