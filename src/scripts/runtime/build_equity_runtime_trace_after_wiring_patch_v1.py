#!/usr/bin/env python3
from __future__ import annotations

import os
import subprocess
from datetime import datetime, timezone, timedelta
from typing import Any

import psycopg2
import psycopg2.extras


# Русский комментарий:
# EQUITY_RUNTIME_TRACE_AFTER_WIRING_PATCH_V1 — schema-safe read-only trace свежих строк.
# Скрипт не меняет БД, runtime, systemd и execution.
# Цель — отделить старые MEAN_REVERSION_EQUITY строки за 24h от новых строк после restart.


RUNTIME_SQL = """
select
    symbol,
    strategy,
    timeframe,
    score,
    priority,
    is_enabled,
    source,
    updated_at
from runtime_active_universe
where symbol = %s
order by is_enabled desc, priority desc nulls last, updated_at desc nulls last
limit 1;
"""


def norm(value: Any) -> str:
    if value is None:
        return ""
    return str(value).strip()


def systemctl_active_since(service: str) -> str:
    try:
        out = subprocess.check_output(
            ["systemctl", "show", service, "-p", "ActiveEnterTimestamp", "--value"],
            text=True,
            stderr=subprocess.DEVNULL,
        ).strip()
        return out or "UNKNOWN"
    except Exception:
        return "UNKNOWN"


def systemctl_active_since_usec(service: str) -> datetime | None:
    """Русский комментарий: надёжно переводит ActiveEnterTimestampUSec systemd в UTC.

    Не парсим руками MSK/локаль. Используем date -d, потому что systemd timestamp
    может быть без микросекунд и с timezone alias.
    """
    try:
        raw = subprocess.check_output(
            ["systemctl", "show", service, "-p", "ActiveEnterTimestampUSec", "--value"],
            text=True,
            stderr=subprocess.DEVNULL,
        ).strip()

        if not raw or raw == "0":
            return None

        # EQUITY_RUNTIME_TRACE_RESTART_AWARE_DATE_CMD_FIX_V1
        # EQUITY_RUNTIME_TRACE_RESTART_AWARE_MSK_REPLACE_FALLBACK_V1
        date_input = raw.replace(" MSK", " +0300")

        iso = subprocess.check_output(
            ["date", "-u", "-d", date_input, "+%Y-%m-%dT%H:%M:%S%z"],
            text=True,
            stderr=subprocess.DEVNULL,
        ).strip()

        parsed = datetime.strptime(iso, "%Y-%m-%dT%H:%M:%S%z")
        return parsed.astimezone(timezone.utc)

    except Exception:
        return None


def table_columns(cur, table_name: str) -> set[str]:
    cur.execute(
        """
        select column_name
        from information_schema.columns
        where table_schema = 'public'
          and table_name = %s
        """,
        (table_name,),
    )
    return {str(r["column_name"]) for r in cur.fetchall()}


def col_expr(cols: set[str], name: str, alias: str | None = None, cast: str = "text") -> str:
    out_name = alias or name
    if name in cols:
        return f"{name} as {out_name}"
    return f"null::{cast} as {out_name}"


def build_guard_sql(cols: set[str]) -> str:
    id_expr = "id" if "id" in cols else "null::bigint as id"
    symbol_expr = col_expr(cols, "symbol")
    strategy_expr = col_expr(cols, "strategy")
    timeframe_expr = col_expr(cols, "timeframe")
    decision_expr = col_expr(cols, "decision")
    reason_expr = col_expr(cols, "reason")
    block_type_expr = col_expr(cols, "block_type")
    block_reason_expr = col_expr(cols, "block_reason")
    created_expr = "created_at" if "created_at" in cols else "null::timestamptz as created_at"

    return f"""
    select
        {id_expr},
        {symbol_expr},
        {strategy_expr},
        {timeframe_expr},
        {decision_expr},
        {reason_expr},
        {block_type_expr},
        {block_reason_expr},
        {created_expr}
    from runtime_guard_pre_signal_block_audit_v1
    where symbol = %s
      and created_at >= greatest(now() - (%s::text)::interval, coalesce(%s::timestamptz, '-infinity'::timestamptz))
    order by created_at desc
    limit %s;
    """


def build_summary_sql(cols: set[str]) -> str:
    if "strategy" in cols:
        expected_expr = "count(*) filter (where strategy = %s) as expected_strategy_rows"
        other_expr = "count(*) filter (where strategy is distinct from %s) as other_strategy_rows"
    else:
        expected_expr = "0::bigint as expected_strategy_rows"
        other_expr = "0::bigint as other_strategy_rows"

    return f"""
    select
        count(*) as rows_total,
        {expected_expr},
        {other_expr},
        max(created_at) as last_created_at
    from runtime_guard_pre_signal_block_audit_v1
    where symbol = %s
      and created_at >= greatest(now() - (%s::text)::interval, coalesce(%s::timestamptz, '-infinity'::timestamptz));
    """


def main() -> int:
    dsn = os.getenv("DATABASE_URL")
    if not dsn:
        raise SystemExit("DATABASE_URL is required")

    symbol = os.getenv("EQUITY_TRACE_SYMBOL", "SBER@MISX")
    expected_strategy = os.getenv("EQUITY_TRACE_STRATEGY", "VOLATILITY_BREAKOUT_EQUITY")
    since_interval = os.getenv("EQUITY_TRACE_SINCE_INTERVAL", "15 minutes")
    limit = int(os.getenv("EQUITY_TRACE_LIMIT", "30"))
    service_name = os.getenv("EQUITY_TRACE_SERVICE", "finam-paper-pipeline.service")

    print("=== EQUITY RUNTIME TRACE AFTER WIRING PATCH V1 ===")
    print("mode=read_only")
    print("runtime_allow=0")
    print("execution_enabled=0")
    print("real_trading_enabled=0")
    print("db_update=0")
    print(f"symbol={symbol}")
    print(f"expected_strategy={expected_strategy}")
    print(f"since_interval={since_interval}")
    # EQUITY_RUNTIME_TRACE_RESTART_AWARE_V1
    service_active_since_text = systemctl_active_since(service_name)
    service_active_since_dt = systemctl_active_since_usec(service_name)

    print(f"service={service_name}")
    print(f"service_active_since={service_active_since_text}")
    print(f"service_active_since_utc={service_active_since_dt.isoformat() if service_active_since_dt else 'UNKNOWN'}")
    print()

    with psycopg2.connect(dsn) as conn:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute(RUNTIME_SQL, (symbol,))
            runtime_row = cur.fetchone()

            guard_cols = table_columns(cur, "runtime_guard_pre_signal_block_audit_v1")
            guard_sql = build_guard_sql(guard_cols)
            summary_sql = build_summary_sql(guard_cols)

            if "strategy" in guard_cols:
                cur.execute(summary_sql, (expected_strategy, expected_strategy, symbol, since_interval, service_active_since_dt))
            else:
                cur.execute(summary_sql, (symbol, since_interval, service_active_since_dt))
            summary = cur.fetchone() or {}

            cur.execute(guard_sql, (symbol, since_interval, service_active_since_dt, limit))
            rows = cur.fetchall()

    print("EQUITY_RUNTIME_AFTER_PATCH_SCHEMA")
    print("guard_table=runtime_guard_pre_signal_block_audit_v1")
    print(f"guard_columns={','.join(sorted(guard_cols))}")
    print(f"has_decision={1 if 'decision' in guard_cols else 0}")
    print(f"has_reason={1 if 'reason' in guard_cols else 0}")
    print(f"has_block_type={1 if 'block_type' in guard_cols else 0}")
    print(f"has_block_reason={1 if 'block_reason' in guard_cols else 0}")
    print()

    print("EQUITY_RUNTIME_AFTER_PATCH_RUNTIME_ROW")
    if runtime_row:
        print(
            "EQUITY_RUNTIME_ROW "
            f"symbol={norm(runtime_row.get('symbol'))} "
            f"strategy={norm(runtime_row.get('strategy'))} "
            f"timeframe={norm(runtime_row.get('timeframe')) or 'UNKNOWN'} "
            f"score={runtime_row.get('score')} "
            f"priority={runtime_row.get('priority')} "
            f"is_enabled={runtime_row.get('is_enabled')} "
            f"source={norm(runtime_row.get('source')) or 'UNKNOWN'} "
            f"updated_at={runtime_row.get('updated_at')}"
        )
    else:
        print("EQUITY_RUNTIME_ROW found=0")

    print()
    print("EQUITY_RUNTIME_AFTER_PATCH_GUARD_ROWS")
    for row in rows:
        decision = norm(row.get("decision")) or norm(row.get("block_type")) or "NULL"
        reason = norm(row.get("reason")) or norm(row.get("block_reason")) or "NULL"
        print(
            "EQUITY_RUNTIME_AFTER_PATCH_GUARD_ROW "
            f"id={row.get('id')} "
            f"symbol={norm(row.get('symbol'))} "
            f"strategy={norm(row.get('strategy')) or 'NULL'} "
            f"timeframe={norm(row.get('timeframe')) or 'NULL'} "
            f"decision={decision} "
            f"reason={reason} "
            f"created_at={row.get('created_at')}"
        )

    rows_total = int(summary.get("rows_total") or 0)
    expected_rows = int(summary.get("expected_strategy_rows") or 0)
    other_rows = int(summary.get("other_strategy_rows") or 0)

    runtime_strategy = norm(runtime_row.get("strategy")) if runtime_row else ""
    runtime_enabled = bool(runtime_row.get("is_enabled")) if runtime_row else False

    print()
    print("EQUITY_RUNTIME_AFTER_PATCH_SUMMARY")
    print(f"runtime_found={1 if runtime_row else 0}")
    print(f"runtime_enabled={1 if runtime_enabled else 0}")
    print(f"runtime_strategy={runtime_strategy or 'NONE'}")
    print(f"fresh_guard_rows={rows_total}")
    print(f"fresh_expected_strategy_rows={expected_rows}")
    print(f"fresh_other_strategy_rows={other_rows}")
    print(f"last_guard_created_at={summary.get('last_created_at')}")
    print(f"restart_aware_filter=1")
    print("runtime_changes_required=0")
    print("execution_changes_required=0")
    print("db_update=0")

    if runtime_strategy != expected_strategy:
        print("diagnosis=RUNTIME_ACTIVE_UNIVERSE_STRATEGY_NOT_EXPECTED")
        print("VERDICT=EQUITY_RUNTIME_AFTER_PATCH_RUNTIME_STRATEGY_MISMATCH")
    elif rows_total == 0:
        print("diagnosis=NO_FRESH_SBER_GUARD_ROWS_AFTER_RESTART")
        print("VERDICT=EQUITY_RUNTIME_AFTER_PATCH_WAIT_FOR_FRESH_ROWS")
    elif expected_rows > 0 and other_rows == 0:
        print("diagnosis=FRESH_ROWS_USE_EXPECTED_STRATEGY")
        print("VERDICT=EQUITY_RUNTIME_AFTER_PATCH_OK")
    elif expected_rows > 0 and other_rows > 0:
        print("diagnosis=MIXED_FRESH_ROWS_EXPECTED_AND_LEGACY")
        print("VERDICT=EQUITY_RUNTIME_AFTER_PATCH_MIXED")
    else:
        print("diagnosis=FRESH_ROWS_STILL_USE_OTHER_STRATEGY")
        print("VERDICT=EQUITY_RUNTIME_AFTER_PATCH_STILL_LEGACY_STRATEGY")

    print("EQUITY_RUNTIME_TRACE_AFTER_WIRING_PATCH_V1_OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
