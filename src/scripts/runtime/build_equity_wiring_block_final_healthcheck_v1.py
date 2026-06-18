#!/usr/bin/env python3
from __future__ import annotations

import os
import subprocess
from typing import Any

import psycopg2
import psycopg2.extras


# Русский комментарий:
# EQUITY_WIRING_BLOCK_FINAL_HEALTHCHECK_V1 — финальная read-only проверка блока equity wiring.
# Скрипт не меняет БД, runtime_active_universe, systemd, execution и real trading.
# Проверяет, что SBER@MISX после restart использует VOLATILITY_BREAKOUT_EQUITY
# в runtime_active_universe и свежих guard rows.


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


GUARD_SUMMARY_SQL = """
select
    count(*) as rows_total,
    count(*) filter (where strategy = %s) as expected_strategy_rows,
    count(*) filter (where strategy is distinct from %s) as other_strategy_rows,
    max(created_at) as last_created_at
from runtime_guard_pre_signal_block_audit_v1
where symbol = %s
  and created_at >= %s::timestamptz;
"""


TRADE_CONTEXT_SQL = """
select
    count(*) as trades_today,
    count(*) filter (
        where coalesce(strategy, '') = ''
           or strategy in ('UNKNOWN', 'UNKNOWN_STRATEGY')
    ) as strategy_missing_today,
    count(*) filter (
        where coalesce(timeframe, '') = ''
           or timeframe in ('UNKNOWN', 'UNKNOWN_TIMEFRAME')
    ) as timeframe_missing_today,
    count(*) filter (
        where coalesce(continuous_symbol, '') = ''
    ) as continuous_symbol_missing_today
from trades
where created_at::date = current_date;
"""


DISCOVERY_SQL = """
select
    count(*) filter (
        where created_at >= now() - interval '1 day'
          and coalesce(status, '') not in ('closed', 'test_closed', 'resolved')
    ) as discovery_new
from signal_strategy_discovery_events;
"""


def norm(value: Any) -> str:
    if value is None:
        return ""
    return str(value).strip()


def active_since_utc(service: str) -> str:
    try:
        raw = subprocess.check_output(
            ["systemctl", "show", service, "-p", "ActiveEnterTimestamp", "--value"],
            text=True,
            stderr=subprocess.DEVNULL,
        ).strip()

        if not raw:
            return ""

        fixed = raw.replace(" MSK", " +0300")
        iso = subprocess.check_output(
            ["date", "-u", "-d", fixed, "+%Y-%m-%dT%H:%M:%S%z"],
            text=True,
            stderr=subprocess.DEVNULL,
        ).strip()

        # PostgreSQL timestamptz принимает +0000, оставляем как есть.
        return iso
    except Exception:
        return ""


def main() -> int:
    dsn = os.getenv("DATABASE_URL")
    if not dsn:
        raise SystemExit("DATABASE_URL is required")

    symbol = os.getenv("EQUITY_HEALTHCHECK_SYMBOL", "SBER@MISX")
    expected_strategy = os.getenv("EQUITY_HEALTHCHECK_STRATEGY", "VOLATILITY_BREAKOUT_EQUITY")
    service = os.getenv("EQUITY_HEALTHCHECK_SERVICE", "finam-paper-pipeline.service")

    service_since = active_since_utc(service)

    print("=== EQUITY WIRING BLOCK FINAL HEALTHCHECK V1 ===")
    print("mode=read_only")
    print("runtime_allow=0")
    print("execution_enabled=0")
    print("real_trading_enabled=0")
    print("db_update=0")
    print(f"symbol={symbol}")
    print(f"expected_strategy={expected_strategy}")
    print(f"service={service}")
    print(f"service_active_since_utc={service_since or 'UNKNOWN'}")
    print()

    with psycopg2.connect(dsn) as conn:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute(RUNTIME_SQL, (symbol,))
            runtime_row = cur.fetchone()

            guard_summary = {
                "rows_total": 0,
                "expected_strategy_rows": 0,
                "other_strategy_rows": 0,
                "last_created_at": None,
            }

            if service_since:
                cur.execute(GUARD_SUMMARY_SQL, (expected_strategy, expected_strategy, symbol, service_since))
                guard_summary = cur.fetchone() or guard_summary

            cur.execute(TRADE_CONTEXT_SQL)
            trade_context = cur.fetchone() or {}

            try:
                cur.execute(DISCOVERY_SQL)
                discovery = cur.fetchone() or {}
            except Exception:
                discovery = {"discovery_new": 0}

    runtime_strategy = norm(runtime_row.get("strategy")) if runtime_row else ""
    runtime_enabled = bool(runtime_row.get("is_enabled")) if runtime_row else False

    guard_rows = int(guard_summary.get("rows_total") or 0)
    guard_expected = int(guard_summary.get("expected_strategy_rows") or 0)
    guard_other = int(guard_summary.get("other_strategy_rows") or 0)

    trades_today = int(trade_context.get("trades_today") or 0)
    strategy_missing = int(trade_context.get("strategy_missing_today") or 0)
    timeframe_missing = int(trade_context.get("timeframe_missing_today") or 0)
    continuous_missing = int(trade_context.get("continuous_symbol_missing_today") or 0)
    discovery_new = int(discovery.get("discovery_new") or 0)

    runtime_ok = bool(runtime_row) and runtime_enabled and runtime_strategy == expected_strategy
    guard_ok = guard_rows > 0 and guard_expected > 0 and guard_other == 0
    trade_context_ok = strategy_missing == 0 and timeframe_missing == 0 and continuous_missing == 0
    discovery_ok = discovery_new == 0
    service_ts_ok = bool(service_since)

    print("EQUITY_WIRING_FINAL_RUNTIME_ROW")
    if runtime_row:
        print(
            "EQUITY_WIRING_RUNTIME_ROW "
            f"symbol={norm(runtime_row.get('symbol'))} "
            f"strategy={runtime_strategy} "
            f"timeframe={norm(runtime_row.get('timeframe')) or 'UNKNOWN'} "
            f"score={runtime_row.get('score')} "
            f"priority={runtime_row.get('priority')} "
            f"is_enabled={runtime_enabled} "
            f"source={norm(runtime_row.get('source')) or 'UNKNOWN'} "
            f"updated_at={runtime_row.get('updated_at')}"
        )
    else:
        print("EQUITY_WIRING_RUNTIME_ROW found=0")

    print()
    print("EQUITY_WIRING_FINAL_GUARD_SUMMARY")
    print(f"guard_rows_after_restart={guard_rows}")
    print(f"guard_expected_strategy_rows={guard_expected}")
    print(f"guard_other_strategy_rows={guard_other}")
    print(f"guard_last_created_at={guard_summary.get('last_created_at')}")

    print()
    print("EQUITY_WIRING_FINAL_TRADE_CONTEXT")
    print(f"trades_today={trades_today}")
    print(f"strategy_missing_today={strategy_missing}")
    print(f"timeframe_missing_today={timeframe_missing}")
    print(f"continuous_symbol_missing_today={continuous_missing}")
    print(f"discovery_new={discovery_new}")

    print()
    print("EQUITY_WIRING_BLOCK_FINAL_HEALTHCHECK_SUMMARY")
    print(f"service_ts_ok={1 if service_ts_ok else 0}")
    print(f"runtime_ok={1 if runtime_ok else 0}")
    print(f"guard_ok={1 if guard_ok else 0}")
    print(f"trade_context_ok={1 if trade_context_ok else 0}")
    print(f"discovery_ok={1 if discovery_ok else 0}")
    print("runtime_changes_required=0")
    print("execution_changes_required=0")
    print("db_update=0")

    all_ok = service_ts_ok and runtime_ok and guard_ok and trade_context_ok and discovery_ok

    if all_ok:
        print("VERDICT=EQUITY_WIRING_BLOCK_FINAL_HEALTHCHECK_OK")
    elif runtime_ok and guard_rows == 0 and trade_context_ok:
        print("VERDICT=EQUITY_WIRING_BLOCK_FINAL_HEALTHCHECK_WAIT_FOR_GUARD_ROWS")
    else:
        print("VERDICT=EQUITY_WIRING_BLOCK_FINAL_HEALTHCHECK_FAIL_REVIEW_REQUIRED")

    print("EQUITY_WIRING_BLOCK_FINAL_HEALTHCHECK_V1_OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
