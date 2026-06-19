#!/usr/bin/env python3
from __future__ import annotations

import os
from typing import Any

import psycopg2
import psycopg2.extras


# Русский комментарий:
# EQUITY_AFTER_PATCH_RUNTIME_OBSERVATION_V1
# Read-only проверка: обрабатывается ли SBER@MISX после restart paper pipeline.
# Цель — отделить "guard patch не работает" от "equity route ещё не дошёл до SBER".


SYMBOL = os.getenv("EQUITY_FLOW_SYMBOL", "SBER@MISX")
STRATEGY = os.getenv("EQUITY_EXPECTED_STRATEGY", "VOLATILITY_BREAKOUT_EQUITY")
TIMEFRAME = os.getenv("EQUITY_TIMEFRAME", "M5")
LOOKBACK_MINUTES = int(os.getenv("EQUITY_AFTER_PATCH_LOOKBACK_MINUTES", "180"))


def sval(value: Any, default: str = "UNKNOWN") -> str:
    if value is None:
        return default
    text = str(value).strip()
    return text if text else default


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
        """
    , (table,))
    result: set[str] = set()
    for row in cur.fetchall():
        if isinstance(row, dict):
            result.add(str(row["column_name"]))
        else:
            result.add(str(row[0]))
    return result


def first_col(cols: set[str], candidates: list[str]) -> str | None:
    for c in candidates:
        if c in cols:
            return c
    return None


def main() -> int:
    dsn = os.getenv("DATABASE_URL")
    if not dsn:
        raise SystemExit("DATABASE_URL is required")

    interval = f"{LOOKBACK_MINUTES} minutes"

    print("=== EQUITY AFTER PATCH RUNTIME OBSERVATION V1 ===")
    print("mode=read_only")
    print("runtime_allow=0")
    print("execution_enabled=0")
    print("real_trading_enabled=0")
    print("db_update=0")
    print(f"symbol={SYMBOL}")
    print(f"strategy={STRATEGY}")
    print(f"timeframe={TIMEFRAME}")
    print(f"lookback_minutes={LOOKBACK_MINUTES}")
    print()

    with psycopg2.connect(dsn) as conn:
        with conn.cursor() as cur:
            has_runtime = table_exists(cur, "runtime_active_universe")
            has_bars = table_exists(cur, "market_bars")
            has_guard = table_exists(cur, "runtime_guard_pre_signal_block_audit_v1")
            has_signals = table_exists(cur, "signals")
            has_intents = table_exists(cur, "execution_intents")
            has_trades = table_exists(cur, "trades")

        runtime_rows = []
        bar_rows = []
        guard_rows = []
        signal_rows = []
        intent_rows = []
        trade_rows = []

        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            if has_runtime:
                cur.execute(
                    """
                    select
                        symbol,
                        strategy,
                        coalesce(timeframe, 'UNKNOWN') as timeframe,
                        coalesce(is_enabled, false) as is_enabled,
                        coalesce(score::text, 'NULL') as score,
                        coalesce(source, 'NULL') as source,
                        coalesce(disable_reason, 'NONE') as disable_reason,
                        updated_at
                    from runtime_active_universe
                    where symbol = %s
                    order by updated_at desc nulls last
                    limit 20
                    """,
                    (SYMBOL,),
                )
                runtime_rows = list(cur.fetchall())

            if has_bars:
                bar_cols = columns(cur, "market_bars")
                ts_col = first_col(bar_cols, ["ts", "timestamp", "bar_time", "created_at"])
                if ts_col:
                    cur.execute(
                        f"""
                        select
                            symbol,
                            timeframe,
                            count(*) as bars,
                            min({ts_col}) as first_ts,
                            max({ts_col}) as last_ts,
                            count(*) filter (where {ts_col} >= now() - (%s::text)::interval) as fresh_bars
                        from market_bars
                        where symbol = %s
                          and timeframe = %s
                        group by symbol, timeframe
                        """,
                        (interval, SYMBOL, TIMEFRAME),
                    )
                    bar_rows = list(cur.fetchall())

            if has_guard:
                cur.execute(
                    """
                    select
                        block_type,
                        block_reason,
                        count(*) as rows,
                        min(created_at) as first_ts,
                        max(created_at) as last_ts
                    from runtime_guard_pre_signal_block_audit_v1
                    where symbol = %s
                      and strategy = %s
                      and created_at >= now() - (%s::text)::interval
                    group by block_type, block_reason
                    order by rows desc
                    """,
                    (SYMBOL, STRATEGY, interval),
                )
                guard_rows = list(cur.fetchall())

            if has_signals:
                sig_cols = columns(cur, "signals")
                ts_col = first_col(sig_cols, ["created_at", "ts", "timestamp", "signal_time"])
                if ts_col and "symbol" in sig_cols:
                    strategy_expr = "coalesce(strategy, 'UNKNOWN')" if "strategy" in sig_cols else "'UNKNOWN'"
                    reason_expr = (
                        "coalesce(signal_class, reason, 'UNKNOWN')"
                        if {"signal_class", "reason"}.issubset(sig_cols)
                        else (
                            "coalesce(signal_class, 'UNKNOWN')"
                            if "signal_class" in sig_cols
                            else (
                                "coalesce(reason, 'UNKNOWN')"
                                if "reason" in sig_cols
                                else "'UNKNOWN'"
                            )
                        )
                    )
                    cur.execute(
                        f"""
                        select
                            {strategy_expr} as strategy,
                            {reason_expr} as reason,
                            count(*) as signals,
                            min({ts_col}) as first_ts,
                            max({ts_col}) as last_ts
                        from signals
                        where symbol = %s
                          and {ts_col} >= now() - (%s::text)::interval
                        group by 1,2
                        order by signals desc
                        """,
                        (SYMBOL, interval),
                    )
                    signal_rows = list(cur.fetchall())

            if has_intents:
                intent_cols = columns(cur, "execution_intents")
                ts_col = first_col(intent_cols, ["created_at", "ts", "timestamp", "updated_at"])
                if ts_col and "symbol" in intent_cols:
                    cur.execute(
                        f"""
                        select
                            count(*) as intents,
                            min({ts_col}) as first_ts,
                            max({ts_col}) as last_ts
                        from execution_intents
                        where symbol = %s
                          and {ts_col} >= now() - (%s::text)::interval
                        """,
                        (SYMBOL, interval),
                    )
                    intent_rows = list(cur.fetchall())

            if has_trades:
                cur.execute(
                    """
                    select
                        coalesce(strategy, 'UNKNOWN') as strategy,
                        coalesce(timeframe, 'UNKNOWN') as timeframe,
                        coalesce(payload->>'trade_source_class', 'UNCLASSIFIED') as trade_source_class,
                        count(*) as trades,
                        min(created_at) as first_ts,
                        max(created_at) as last_ts
                    from trades
                    where symbol = %s
                      and created_at >= now() - (%s::text)::interval
                      and coalesce(is_invalid, false) = false
                    group by 1,2,3
                    order by trades desc
                    """,
                    (SYMBOL, interval),
                )
                trade_rows = list(cur.fetchall())

    print("EQUITY_AFTER_PATCH_RUNTIME_ROWS")
    for r in runtime_rows:
        print(
            "EQUITY_AFTER_PATCH_RUNTIME_ROW "
            f"symbol={r['symbol']} "
            f"strategy={r['strategy']} "
            f"timeframe={r['timeframe']} "
            f"is_enabled={int(bool(r['is_enabled']))} "
            f"score={r['score']} "
            f"source={r['source']} "
            f"disable_reason={r['disable_reason']} "
            f"updated_at={r['updated_at']}"
        )

    print()
    print("EQUITY_AFTER_PATCH_BAR_ROWS")
    fresh_bars_total = 0
    bars_total = 0
    for r in bar_rows:
        bars_total += int(r["bars"])
        fresh_bars_total += int(r["fresh_bars"])
        print(
            "EQUITY_AFTER_PATCH_BAR_ROW "
            f"symbol={r['symbol']} "
            f"timeframe={r['timeframe']} "
            f"bars={r['bars']} "
            f"fresh_bars={r['fresh_bars']} "
            f"first_ts={r['first_ts']} "
            f"last_ts={r['last_ts']}"
        )

    print()
    print("EQUITY_AFTER_PATCH_GUARD_GROUP_ROWS")
    guard_total = 0
    br_reason_rows = 0
    equity_reason_rows = 0
    for r in guard_rows:
        rows = int(r["rows"])
        guard_total += rows
        reason = sval(r["block_reason"])
        if reason == "br_volatility_too_low":
            br_reason_rows += rows
        if reason == "equity_volatility_too_low":
            equity_reason_rows += rows
        print(
            "EQUITY_AFTER_PATCH_GUARD_GROUP_ROW "
            f"block_type={sval(r['block_type'])} "
            f"reason={reason} "
            f"rows={rows} "
            f"first_ts={r['first_ts']} "
            f"last_ts={r['last_ts']}"
        )

    print()
    print("EQUITY_AFTER_PATCH_SIGNAL_ROWS")
    signal_total = 0
    for r in signal_rows:
        signals = int(r["signals"])
        signal_total += signals
        print(
            "EQUITY_AFTER_PATCH_SIGNAL_ROW "
            f"strategy={sval(r['strategy'])} "
            f"reason={sval(r['reason'])} "
            f"signals={signals} "
            f"first_ts={r['first_ts']} "
            f"last_ts={r['last_ts']}"
        )

    print()
    print("EQUITY_AFTER_PATCH_INTENT_ROWS")
    intent_total = 0
    for r in intent_rows:
        intent_total += int(r["intents"] or 0)
        print(
            "EQUITY_AFTER_PATCH_INTENT_ROW "
            f"intents={r['intents']} "
            f"first_ts={r['first_ts']} "
            f"last_ts={r['last_ts']}"
        )

    print()
    print("EQUITY_AFTER_PATCH_TRADE_ROWS")
    trade_total = 0
    clean_trade_total = 0
    for r in trade_rows:
        trades = int(r["trades"])
        trade_total += trades
        if r["trade_source_class"] == "RUNTIME_OR_PAPER_CLEAN_ENOUGH":
            clean_trade_total += trades
        print(
            "EQUITY_AFTER_PATCH_TRADE_ROW "
            f"strategy={sval(r['strategy'])} "
            f"timeframe={sval(r['timeframe'])} "
            f"trade_source_class={sval(r['trade_source_class'])} "
            f"trades={trades} "
            f"first_ts={r['first_ts']} "
            f"last_ts={r['last_ts']}"
        )

    runtime_ok = any(
        r["symbol"] == SYMBOL
        and r["strategy"] == STRATEGY
        and r["timeframe"] == TIMEFRAME
        and bool(r["is_enabled"])
        for r in runtime_rows
    )

    print()
    print("EQUITY_AFTER_PATCH_RUNTIME_OBSERVATION_SUMMARY")
    print(f"runtime_ok={int(runtime_ok)}")
    print(f"bars_total={bars_total}")
    print(f"fresh_bars_total={fresh_bars_total}")
    print(f"fresh_guard_rows={guard_total}")
    print(f"fresh_signals={signal_total}")
    print(f"fresh_intents={intent_total}")
    print(f"fresh_trades={trade_total}")
    print(f"fresh_clean_trades={clean_trade_total}")
    print(f"equity_volatility_reason_rows={equity_reason_rows}")
    print(f"br_volatility_reason_rows={br_reason_rows}")
    print("db_update=0")
    print("runtime_changes_required=0")
    print("execution_changes_required=0")
    print("real_trading_enabled=0")
    print("execution_enabled=0")

    if not runtime_ok:
        print("VERDICT=EQUITY_AFTER_PATCH_RUNTIME_NOT_ENABLED")
    elif fresh_bars_total == 0:
        print("VERDICT=EQUITY_AFTER_PATCH_NO_FRESH_BARS")
    elif guard_total == 0 and signal_total == 0:
        print("VERDICT=EQUITY_AFTER_PATCH_BARS_OK_NO_GUARD_OR_SIGNAL")
    elif br_reason_rows > 0:
        print("VERDICT=EQUITY_AFTER_PATCH_BR_REASON_STILL_PRESENT")
    elif equity_reason_rows > 0:
        print("VERDICT=EQUITY_AFTER_PATCH_EQUITY_GUARD_CONFIRMED")
    elif signal_total > 0:
        print("VERDICT=EQUITY_AFTER_PATCH_SIGNAL_PROGRESS")
    else:
        print("VERDICT=EQUITY_AFTER_PATCH_REVIEW_REQUIRED")

    print("EQUITY_AFTER_PATCH_RUNTIME_OBSERVATION_V1_OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
