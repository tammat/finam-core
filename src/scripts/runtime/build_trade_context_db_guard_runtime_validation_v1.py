#!/usr/bin/env python3
from __future__ import annotations

import os
import subprocess
from typing import Any

import psycopg2
import psycopg2.extras


# Русский комментарий:
# TRADE_CONTEXT_DB_GUARD_RUNTIME_VALIDATION_V1
# Проверяет runtime-эффект PostgreSQL trigger trade_context_guard_trades_before_write_v1.
# Скрипт read-only: БД, runtime, execution и real trading не меняет.


SERVICE = os.getenv("TRADE_CONTEXT_GUARD_SERVICE", "finam-paper-pipeline.service")


TRIGGER_SQL = """
select
    tgname as trigger_name,
    tgenabled as enabled
from pg_trigger
where tgname = 'trade_context_guard_trades_before_write_v1';
"""


TOTAL_AFTER_SQL = """
select
    count(*) as trades_after_restart,
    count(*) filter (
        where symbol in ('USDRUBF@RTSX', 'NGM6@RTSX', 'NGN6@RTSX', 'BRN6@RTSX')
    ) as known_route_trades_after_restart,
    max(created_at) as last_trade_after_restart
from trades
where created_at >= %s::timestamptz;
"""


UNKNOWN_AFTER_SQL = """
select
    id,
    created_at,
    symbol,
    side,
    qty,
    price,
    strategy,
    timeframe,
    continuous_symbol,
    trade_source,
    origin,
    fill_id
from trades
where created_at >= %s::timestamptz
  and (
        coalesce(strategy, '') = ''
     or strategy in ('UNKNOWN', 'UNKNOWN_STRATEGY')
     or coalesce(timeframe, '') = ''
     or timeframe in ('UNKNOWN', 'UNKNOWN_TIMEFRAME')
     or coalesce(continuous_symbol, '') = ''
  )
order by created_at asc, id asc;
"""


KNOWN_ROUTE_SQL = """
select
    symbol,
    coalesce(strategy, 'UNKNOWN') as strategy,
    coalesce(timeframe, 'UNKNOWN') as timeframe,
    coalesce(continuous_symbol, 'UNKNOWN') as continuous_symbol,
    count(*) as trades,
    min(created_at) as first_trade,
    max(created_at) as last_trade
from trades
where created_at >= %s::timestamptz
  and symbol in ('USDRUBF@RTSX', 'NGM6@RTSX', 'NGN6@RTSX', 'BRN6@RTSX')
group by symbol, strategy, timeframe, continuous_symbol
order by symbol, strategy, timeframe, continuous_symbol;
"""


TODAY_UNKNOWN_SQL = """
select
    count(*) as today_unknown_rows
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
        return subprocess.check_output(
            ["date", "-u", "-d", fixed, "+%Y-%m-%dT%H:%M:%S%z"],
            text=True,
            stderr=subprocess.DEVNULL,
        ).strip()
    except Exception:
        return ""


def fmt(value: Any) -> str:
    if value is None:
        return "NULL"
    return str(value)


def main() -> int:
    dsn = os.getenv("DATABASE_URL")
    if not dsn:
        raise SystemExit("DATABASE_URL is required")

    service_since = active_since_utc(SERVICE)

    print("=== TRADE CONTEXT DB GUARD RUNTIME VALIDATION V1 ===")
    print("mode=read_only")
    print("runtime_allow=0")
    print("execution_enabled=0")
    print("real_trading_enabled=0")
    print("db_update=0")
    print(f"service={SERVICE}")
    print(f"service_active_since_utc={service_since or 'UNKNOWN'}")
    print()

    with psycopg2.connect(dsn) as conn:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute(TRIGGER_SQL)
            trigger_rows = cur.fetchall()

            if not service_since:
                totals = {}
                unknown_rows = []
                known_rows = []
            else:
                cur.execute(TOTAL_AFTER_SQL, (service_since,))
                totals = cur.fetchone() or {}

                cur.execute(UNKNOWN_AFTER_SQL, (service_since,))
                unknown_rows = cur.fetchall()

                cur.execute(KNOWN_ROUTE_SQL, (service_since,))
                known_rows = cur.fetchall()

            cur.execute(TODAY_UNKNOWN_SQL)
            today_unknown = cur.fetchone() or {}

    trigger_found = 1 if trigger_rows else 0
    trigger_enabled = 1 if any(str(r.get("enabled")) == "O" for r in trigger_rows) else 0

    print("TRADE_CONTEXT_DB_GUARD_TRIGGER")
    for row in trigger_rows:
        print(
            "TRADE_CONTEXT_DB_GUARD_TRIGGER_ROW "
            f"trigger_name={fmt(row.get('trigger_name'))} "
            f"enabled={fmt(row.get('enabled'))}"
        )

    print()
    print("TRADE_CONTEXT_DB_GUARD_RUNTIME_KNOWN_ROUTE_ROWS")
    for row in known_rows:
        print(
            "TRADE_CONTEXT_DB_GUARD_RUNTIME_KNOWN_ROUTE_ROW "
            f"symbol={fmt(row.get('symbol'))} "
            f"strategy={fmt(row.get('strategy'))} "
            f"timeframe={fmt(row.get('timeframe'))} "
            f"continuous_symbol={fmt(row.get('continuous_symbol'))} "
            f"trades={fmt(row.get('trades'))} "
            f"first_trade={fmt(row.get('first_trade'))} "
            f"last_trade={fmt(row.get('last_trade'))}"
        )

    print()
    print("TRADE_CONTEXT_DB_GUARD_RUNTIME_UNKNOWN_ROWS")
    for row in unknown_rows:
        print(
            "TRADE_CONTEXT_DB_GUARD_RUNTIME_UNKNOWN_ROW "
            f"id={fmt(row.get('id'))} "
            f"created_at={fmt(row.get('created_at'))} "
            f"symbol={fmt(row.get('symbol'))} "
            f"side={fmt(row.get('side'))} "
            f"qty={fmt(row.get('qty'))} "
            f"price={fmt(row.get('price'))} "
            f"strategy={fmt(row.get('strategy'))} "
            f"timeframe={fmt(row.get('timeframe'))} "
            f"continuous_symbol={fmt(row.get('continuous_symbol'))} "
            f"trade_source={fmt(row.get('trade_source'))} "
            f"origin={fmt(row.get('origin'))} "
            f"fill_id={fmt(row.get('fill_id'))}"
        )

    trades_after = int(totals.get("trades_after_restart") or 0)
    known_after = int(totals.get("known_route_trades_after_restart") or 0)
    unknown_after = len(unknown_rows)
    today_unknown_rows = int(today_unknown.get("today_unknown_rows") or 0)

    print()
    print("TRADE_CONTEXT_DB_GUARD_RUNTIME_VALIDATION_SUMMARY")
    print(f"trigger_found={trigger_found}")
    print(f"trigger_enabled={trigger_enabled}")
    print(f"service_ts_ok={1 if service_since else 0}")
    print(f"trades_after_restart={trades_after}")
    print(f"known_route_trades_after_restart={known_after}")
    print(f"unknown_after_restart={unknown_after}")
    print(f"today_unknown_rows={today_unknown_rows}")
    print(f"last_trade_after_restart={fmt(totals.get('last_trade_after_restart'))}")
    print("runtime_changes_required=0")
    print("execution_changes_required=0")
    print("db_update=0")

    if not trigger_found or not trigger_enabled:
        print("VERDICT=TRADE_CONTEXT_DB_GUARD_TRIGGER_NOT_READY")
    elif trades_after == 0:
        print("VERDICT=TRADE_CONTEXT_DB_GUARD_RUNTIME_WAIT_FOR_TRADES")
    elif unknown_after == 0 and today_unknown_rows == 0:
        print("VERDICT=TRADE_CONTEXT_DB_GUARD_RUNTIME_VALIDATION_OK")
    elif unknown_after > 0:
        print("VERDICT=TRADE_CONTEXT_DB_GUARD_RUNTIME_FAILED_NEW_UNKNOWN_ROWS")
    else:
        print("VERDICT=TRADE_CONTEXT_DB_GUARD_TODAY_BACKLOG_REQUIRES_APPLY")

    print("TRADE_CONTEXT_DB_GUARD_RUNTIME_VALIDATION_V1_OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
