#!/usr/bin/env python3
from __future__ import annotations

import os
import subprocess
from typing import Any

import psycopg2
import psycopg2.extras


# Русский комментарий:
# RUNTIME_ACCUMULATION_RESUME_V1
# Read-only контроль возобновления runtime accumulation после блокировки USDRUB_REGIME.
# Скрипт ничего не меняет в БД, runtime, execution и real trading.


SERVICE = os.getenv("FINAM_RUNTIME_SERVICE", "finam-paper-pipeline.service")


TODAY_TRADES_SQL = """
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


UNKNOWN_CONTEXT_SQL = """
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


RECENT_AFTER_BLOCK_SQL = """
select
    symbol,
    strategy,
    timeframe,
    continuous_symbol,
    count(*) as trades_after_block,
    min(created_at) as first_trade_after_block,
    max(created_at) as last_trade_after_block
from trades
where created_at >= %s::timestamptz
  and coalesce(is_invalid, false) = false
group by symbol, strategy, timeframe, continuous_symbol
order by trades_after_block desc, symbol, strategy, timeframe;
"""


USDRUB_AFTER_BLOCK_SQL = """
select
    count(*) as usdrub_trades_after_block,
    max(created_at) as usdrub_last_trade_after_block
from trades
where created_at >= %s::timestamptz
  and symbol = 'USDRUBF@RTSX'
  and strategy = 'USDRUB_REGIME'
  and coalesce(is_invalid, false) = false;
"""


RUNTIME_SELECTION_SQL = """
select
    symbol,
    strategy,
    mode,
    enabled,
    reason
from runtime_strategy_selection
where symbol = 'USDRUBF@RTSX'
   or strategy = 'USDRUB_REGIME'
order by updated_at desc nulls last
limit 10;
"""


RUNTIME_ACTIVE_SQL = """
select
    symbol,
    strategy,
    timeframe,
    is_enabled,
    source,
    updated_at,
    disabled_at,
    disable_reason
from runtime_active_universe
order by is_enabled desc, priority desc nulls last, score desc nulls last, updated_at desc nulls last
limit 30;
"""


def fmt(value: Any) -> str:
    if value is None:
        return "NULL"
    return str(value)


def service_active_since_utc(service: str) -> str:
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


def git_head() -> str:
    try:
        return subprocess.check_output(
            ["git", "rev-parse", "--short", "HEAD"],
            text=True,
            stderr=subprocess.DEVNULL,
        ).strip()
    except Exception:
        return "UNKNOWN"


def main() -> int:
    dsn = os.getenv("DATABASE_URL")
    if not dsn:
        raise SystemExit("DATABASE_URL is required")

    since_ts = os.getenv("RUNTIME_ACCUMULATION_RESUME_SINCE_UTC", "").strip()
    if not since_ts:
        since_ts = service_active_since_utc(SERVICE)

    print("=== RUNTIME ACCUMULATION RESUME V1 ===")
    print("mode=read_only")
    print("runtime_allow=0")
    print("execution_enabled=0")
    print("real_trading_enabled=0")
    print("db_update=0")
    print(f"git_head={git_head()}")
    print(f"service={SERVICE}")
    print(f"service_active_since_utc={since_ts or 'UNKNOWN'}")
    print()

    with psycopg2.connect(dsn) as conn:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute(TODAY_TRADES_SQL)
            today_rows = cur.fetchall()

            cur.execute(UNKNOWN_CONTEXT_SQL)
            unknown_row = cur.fetchone() or {}

            cur.execute(RUNTIME_SELECTION_SQL)
            selection_rows = cur.fetchall()

            cur.execute(RUNTIME_ACTIVE_SQL)
            active_rows = cur.fetchall()

            if since_ts:
                cur.execute(RECENT_AFTER_BLOCK_SQL, (since_ts,))
                after_rows = cur.fetchall()

                cur.execute(USDRUB_AFTER_BLOCK_SQL, (since_ts,))
                usdrub_after = cur.fetchone() or {}
            else:
                after_rows = []
                usdrub_after = {}

    print("RUNTIME_ACCUMULATION_TODAY_ROWS")
    for row in today_rows:
        print(
            "RUNTIME_ACCUMULATION_TODAY_ROW "
            f"symbol={fmt(row.get('symbol'))} "
            f"strategy={fmt(row.get('strategy'))} "
            f"timeframe={fmt(row.get('timeframe'))} "
            f"continuous_symbol={fmt(row.get('continuous_symbol'))} "
            f"trades={fmt(row.get('trades'))} "
            f"first_trade={fmt(row.get('first_trade'))} "
            f"last_trade={fmt(row.get('last_trade'))}"
        )

    print()
    print("RUNTIME_ACCUMULATION_AFTER_BLOCK_ROWS")
    for row in after_rows:
        print(
            "RUNTIME_ACCUMULATION_AFTER_BLOCK_ROW "
            f"symbol={fmt(row.get('symbol'))} "
            f"strategy={fmt(row.get('strategy'))} "
            f"timeframe={fmt(row.get('timeframe'))} "
            f"continuous_symbol={fmt(row.get('continuous_symbol'))} "
            f"trades_after_block={fmt(row.get('trades_after_block'))} "
            f"first_trade_after_block={fmt(row.get('first_trade_after_block'))} "
            f"last_trade_after_block={fmt(row.get('last_trade_after_block'))}"
        )

    print()
    print("RUNTIME_ACCUMULATION_USDRUB_SELECTION_ROWS")
    blocked_selection_rows = 0
    for row in selection_rows:
        mode = str(row.get("mode") or "").upper()
        enabled = row.get("enabled")
        enabled_text = str(enabled).lower()
        is_blocked = mode == "BLOCKED" or enabled is False or enabled_text in {"false", "f", "0", "no"}
        if is_blocked:
            blocked_selection_rows += 1

        print(
            "RUNTIME_ACCUMULATION_USDRUB_SELECTION_ROW "
            f"symbol={fmt(row.get('symbol'))} "
            f"strategy={fmt(row.get('strategy'))} "
            f"mode={fmt(row.get('mode'))} "
            f"enabled={fmt(row.get('enabled'))} "
            f"reason={fmt(row.get('reason'))} "
            f"is_blocked={1 if is_blocked else 0}"
        )

    print()
    print("RUNTIME_ACCUMULATION_ACTIVE_UNIVERSE_ROWS")
    active_enabled_count = 0
    for row in active_rows:
        is_enabled = str(row.get("is_enabled")).lower() in {"true", "t", "1"}
        if is_enabled:
            active_enabled_count += 1

        print(
            "RUNTIME_ACCUMULATION_ACTIVE_UNIVERSE_ROW "
            f"symbol={fmt(row.get('symbol'))} "
            f"strategy={fmt(row.get('strategy'))} "
            f"timeframe={fmt(row.get('timeframe'))} "
            f"is_enabled={fmt(row.get('is_enabled'))} "
            f"source={fmt(row.get('source'))} "
            f"updated_at={fmt(row.get('updated_at'))} "
            f"disabled_at={fmt(row.get('disabled_at'))} "
            f"disable_reason={fmt(row.get('disable_reason'))}"
        )

    unknown_rows = int(unknown_row.get("unknown_rows") or 0)
    usdrub_after_count = int(usdrub_after.get("usdrub_trades_after_block") or 0)

    today_total = sum(int(row.get("trades") or 0) for row in today_rows)
    active_symbols = ",".join(
        str(row.get("symbol"))
        for row in active_rows
        if str(row.get("is_enabled")).lower() in {"true", "t", "1"}
    )

    print()
    print("RUNTIME_ACCUMULATION_RESUME_SUMMARY")
    print(f"today_symbols={len(today_rows)}")
    print(f"today_trades_total={today_total}")
    print(f"today_unknown_rows={unknown_rows}")
    print(f"blocked_usdrub_selection_rows={blocked_selection_rows}")
    print(f"usdrub_trades_after_service_start={usdrub_after_count}")
    print(f"usdrub_last_trade_after_service_start={fmt(usdrub_after.get('usdrub_last_trade_after_block'))}")
    print(f"active_universe_rows={len(active_rows)}")
    print(f"active_enabled_count={active_enabled_count}")
    print(f"active_enabled_symbols={active_symbols}")
    print("runtime_changes_required=0")
    print("execution_changes_required=0")
    print("db_update=0")

    if unknown_rows > 0:
        print("VERDICT=RUNTIME_ACCUMULATION_CONTEXT_DIRTY")
    elif blocked_selection_rows == 0:
        print("VERDICT=RUNTIME_ACCUMULATION_USDRUB_BLOCK_NOT_CONFIRMED")
    elif usdrub_after_count > 0:
        print("VERDICT=RUNTIME_ACCUMULATION_USDRUB_STILL_TRADING")
    elif today_total == 0:
        print("VERDICT=RUNTIME_ACCUMULATION_WAIT_FOR_TRADES")
    else:
        print("VERDICT=RUNTIME_ACCUMULATION_RESUME_OK")

    print("RUNTIME_ACCUMULATION_RESUME_V1_OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
