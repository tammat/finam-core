#!/usr/bin/env python3
from __future__ import annotations

import os
from collections import Counter
from typing import Any

import psycopg2
import psycopg2.extras


# Русский комментарий:
# EQUITY_SHADOW_EDGE_SCORECARD_V1
# Read-only проверка equity shadow слоя.
# Цель — понять, есть ли по акциям данные для допуска к paper/real path.
# Ничего не обновляет в БД.


LOOKBACK_DAYS = int(os.getenv("EQUITY_SHADOW_LOOKBACK_DAYS", "30"))


def sval(value: Any, default: str = "UNKNOWN") -> str:
    if value is None:
        return default
    text = str(value).strip()
    return text if text else default


def fnum(value: Any) -> float:
    try:
        return float(value or 0.0)
    except Exception:
        return 0.0


def table_exists(cur, table: str) -> bool:
    cur.execute(
        """
        select exists (
            select 1
            from information_schema.tables
            where table_schema = 'public'
              and table_name = %s
        )
        """,
        (table,),
    )
    return bool(cur.fetchone()[0])


def columns(cur, table: str) -> set[str]:
    cur.execute(
        """
        select column_name
        from information_schema.columns
        where table_schema = 'public'
          and table_name = %s
        """,
        (table,),
    )

    # Русский комментарий:
    # Cursor может быть обычным tuple cursor или RealDictCursor.
    # Поэтому читаем column_name безопасно для обоих вариантов.
    result: set[str] = set()
    for row in cur.fetchall():
        if isinstance(row, dict):
            result.add(str(row["column_name"]))
        else:
            result.add(str(row[0]))
    return result


def first_existing(cols: set[str], candidates: list[str]) -> str | None:
    for c in candidates:
        if c in cols:
            return c
    return None


def main() -> int:
    dsn = os.getenv("DATABASE_URL")
    if not dsn:
        raise SystemExit("DATABASE_URL is required")

    interval = f"{LOOKBACK_DAYS} days"

    print("=== EQUITY SHADOW EDGE SCORECARD V1 ===")
    print("mode=read_only")
    print("runtime_allow=0")
    print("execution_enabled=0")
    print("real_trading_enabled=0")
    print("db_update=0")
    print(f"lookback_days={LOOKBACK_DAYS}")
    print()

    with psycopg2.connect(dsn) as conn:
        with conn.cursor() as cur:
            has_runtime = table_exists(cur, "runtime_active_universe")
            has_bars = table_exists(cur, "market_bars")
            has_trades = table_exists(cur, "trades")
            has_signals = table_exists(cur, "signals")
            has_execution_intents = table_exists(cur, "execution_intents")

        runtime_rows = []
        bar_rows = []
        signal_rows = []
        intent_rows = []
        trade_rows = []

        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            if has_runtime:
                cols = columns(cur, "runtime_active_universe")
                if {"symbol", "strategy"}.issubset(cols):
                    cur.execute(
                        """
                        select
                            symbol,
                            strategy,
                            coalesce(timeframe, 'UNKNOWN') as timeframe,
                            coalesce(is_enabled, false) as is_enabled,
                            coalesce(disable_reason, '') as disable_reason
                        from runtime_active_universe
                        where symbol like %s
                        order by symbol, strategy, timeframe
                        """,
                        ("%@MISX",),
                    )
                    runtime_rows = list(cur.fetchall())

            if has_bars:
                cols = columns(cur, "market_bars")
                ts_col = first_existing(cols, ["ts", "timestamp", "bar_time", "created_at"])
                if {"symbol", "timeframe"}.issubset(cols) and ts_col:
                    cur.execute(
                        f"""
                        select
                            symbol,
                            timeframe,
                            count(*) as bars,
                            min({ts_col}) as first_ts,
                            max({ts_col}) as last_ts
                        from market_bars
                        where symbol like %s
                          and {ts_col} >= now() - (%s::text)::interval
                        group by symbol, timeframe
                        order by symbol, timeframe
                        """,
                        ("%@MISX", interval),
                    )
                    bar_rows = list(cur.fetchall())

            if has_signals:
                cols = columns(cur, "signals")
                ts_col = first_existing(cols, ["created_at", "ts", "timestamp", "signal_time"])
                if "symbol" in cols and ts_col:
                    strategy_expr = "coalesce(strategy, 'UNKNOWN')" if "strategy" in cols else "'UNKNOWN'"
                    timeframe_expr = "coalesce(timeframe, 'UNKNOWN')" if "timeframe" in cols else "'UNKNOWN'"
                    signal_class_expr = "coalesce(signal_class, reason, 'UNKNOWN')" if "signal_class" in cols and "reason" in cols else (
                        "coalesce(signal_class, 'UNKNOWN')" if "signal_class" in cols else (
                            "coalesce(reason, 'UNKNOWN')" if "reason" in cols else "'UNKNOWN'"
                        )
                    )
                    cur.execute(
                        f"""
                        select
                            symbol,
                            {strategy_expr} as strategy,
                            {timeframe_expr} as timeframe,
                            {signal_class_expr} as signal_class,
                            count(*) as signals
                        from signals
                        where symbol like %s
                          and {ts_col} >= now() - (%s::text)::interval
                        group by 1,2,3,4
                        order by signals desc, symbol
                        """,
                        ("%@MISX", interval),
                    )
                    signal_rows = list(cur.fetchall())

            if has_execution_intents:
                cols = columns(cur, "execution_intents")
                ts_col = first_existing(cols, ["created_at", "ts", "timestamp"])
                if "symbol" in cols and ts_col:
                    strategy_expr = "coalesce(strategy, 'UNKNOWN')" if "strategy" in cols else "'UNKNOWN'"
                    status_expr = "coalesce(status, 'UNKNOWN')" if "status" in cols else "'UNKNOWN'"
                    cur.execute(
                        f"""
                        select
                            symbol,
                            {strategy_expr} as strategy,
                            {status_expr} as status,
                            count(*) as intents
                        from execution_intents
                        where symbol like %s
                          and {ts_col} >= now() - (%s::text)::interval
                        group by 1,2,3
                        order by intents desc, symbol
                        """,
                        ("%@MISX", interval),
                    )
                    intent_rows = list(cur.fetchall())

            if has_trades:
                cols = columns(cur, "trades")
                if {"symbol", "created_at"}.issubset(cols):
                    cur.execute(
                        """
                        select
                            symbol,
                            coalesce(strategy, 'UNKNOWN') as strategy,
                            coalesce(timeframe, 'UNKNOWN') as timeframe,
                            coalesce(payload->>'trade_source_class', 'UNCLASSIFIED') as trade_source_class,
                            count(*) as trades,
                            coalesce(sum(commission), 0) as commission
                        from trades
                        where symbol like %s
                          and created_at >= now() - (%s::text)::interval
                          and coalesce(is_invalid, false) = false
                        group by 1,2,3,4
                        order by trades desc, symbol
                        """,
                        ("%@MISX", interval),
                    )
                    trade_rows = list(cur.fetchall())

    print("EQUITY_RUNTIME_ROWS")
    enabled_equities = 0
    for r in runtime_rows:
        if r["is_enabled"]:
            enabled_equities += 1
        print(
            "EQUITY_RUNTIME_ROW "
            f"symbol={r['symbol']} "
            f"strategy={r['strategy']} "
            f"timeframe={r['timeframe']} "
            f"is_enabled={int(bool(r['is_enabled']))} "
            f"disable_reason={sval(r['disable_reason'], 'NONE')}"
        )

    print()
    print("EQUITY_BAR_ROWS")
    symbols_with_bars = set()
    for r in bar_rows:
        symbols_with_bars.add(r["symbol"])
        print(
            "EQUITY_BAR_ROW "
            f"symbol={r['symbol']} "
            f"timeframe={r['timeframe']} "
            f"bars={r['bars']} "
            f"first_ts={r['first_ts']} "
            f"last_ts={r['last_ts']}"
        )

    print()
    print("EQUITY_SIGNAL_ROWS")
    signal_total = 0
    for r in signal_rows:
        signal_total += int(r["signals"])
        print(
            "EQUITY_SIGNAL_ROW "
            f"symbol={r['symbol']} "
            f"strategy={r['strategy']} "
            f"timeframe={r['timeframe']} "
            f"signal_class={r['signal_class']} "
            f"signals={r['signals']}"
        )

    print()
    print("EQUITY_INTENT_ROWS")
    intent_total = 0
    for r in intent_rows:
        intent_total += int(r["intents"])
        print(
            "EQUITY_INTENT_ROW "
            f"symbol={r['symbol']} "
            f"strategy={r['strategy']} "
            f"status={r['status']} "
            f"intents={r['intents']}"
        )

    print()
    print("EQUITY_TRADE_ROWS")
    trade_total = 0
    clean_trade_total = 0
    for r in trade_rows:
        trades = int(r["trades"])
        trade_total += trades
        if r["trade_source_class"] == "RUNTIME_OR_PAPER_CLEAN_ENOUGH":
            clean_trade_total += trades
        print(
            "EQUITY_TRADE_ROW "
            f"symbol={r['symbol']} "
            f"strategy={r['strategy']} "
            f"timeframe={r['timeframe']} "
            f"trade_source_class={r['trade_source_class']} "
            f"trades={trades} "
            f"commission={fnum(r['commission']):.6f}"
        )

    runtime_symbols = {r["symbol"] for r in runtime_rows}
    enabled_symbols = {r["symbol"] for r in runtime_rows if r["is_enabled"]}
    bar_symbols = symbols_with_bars

    print()
    print("EQUITY_SHADOW_EDGE_SCORECARD_SUMMARY")
    print(f"runtime_equity_rows={len(runtime_rows)}")
    print(f"enabled_equities={enabled_equities}")
    print(f"equities_with_bars={len(bar_symbols)}")
    print(f"equities_enabled_with_bars={len(enabled_symbols & bar_symbols)}")
    print(f"signals_total={signal_total}")
    print(f"execution_intents_total={intent_total}")
    print(f"equity_trades_total={trade_total}")
    print(f"equity_clean_runtime_trades={clean_trade_total}")
    print("db_update=0")
    print("runtime_changes_required=0")
    print("execution_changes_required=0")
    print("real_trading_enabled=0")
    print("execution_enabled=0")

    if clean_trade_total > 0:
        print("VERDICT=EQUITY_SHADOW_HAS_CLEAN_TRADE_DATA")
    elif signal_total > 0 or intent_total > 0:
        print("VERDICT=EQUITY_SHADOW_HAS_SIGNALS_NO_CLEAN_TRADES")
    elif len(enabled_symbols & bar_symbols) > 0:
        print("VERDICT=EQUITY_SHADOW_BARS_OK_NO_SIGNALS")
    elif enabled_equities > 0:
        print("VERDICT=EQUITY_SHADOW_ENABLED_NO_BARS")
    else:
        print("VERDICT=EQUITY_SHADOW_NOT_ACTIVE")

    print("EQUITY_SHADOW_EDGE_SCORECARD_V1_OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
