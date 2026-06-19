#!/usr/bin/env python3
from __future__ import annotations

import os
from typing import Any

import psycopg2
import psycopg2.extras


# Русский комментарий:
# EQUITY_SIGNAL_TO_INTENT_FLOW_AUDIT_V1
# Read-only аудит маршрута equity:
# runtime_active_universe -> market_bars -> signals -> execution_intents -> trades.
# Фокус: почему по SBER есть execution_intents, но signals_total=0.


SYMBOL = os.getenv("EQUITY_FLOW_SYMBOL", "SBER@MISX")
LOOKBACK_DAYS = int(os.getenv("EQUITY_FLOW_LOOKBACK_DAYS", "30"))


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
        """,
        (table,),
    )
    result: set[str] = set()
    for row in cur.fetchall():
        if isinstance(row, dict):
            result.add(str(row["column_name"]))
        else:
            result.add(str(row[0]))
    return result


def first_col(cols: set[str], names: list[str]) -> str | None:
    for name in names:
        if name in cols:
            return name
    return None


def main() -> int:
    dsn = os.getenv("DATABASE_URL")
    if not dsn:
        raise SystemExit("DATABASE_URL is required")

    interval = f"{LOOKBACK_DAYS} days"

    print("=== EQUITY SIGNAL TO INTENT FLOW AUDIT V1 ===")
    print("mode=read_only")
    print("runtime_allow=0")
    print("execution_enabled=0")
    print("real_trading_enabled=0")
    print("db_update=0")
    print(f"symbol={SYMBOL}")
    print(f"lookback_days={LOOKBACK_DAYS}")
    print()

    with psycopg2.connect(dsn) as conn:
        with conn.cursor() as cur:
            has_runtime = table_exists(cur, "runtime_active_universe")
            has_bars = table_exists(cur, "market_bars")
            has_signals = table_exists(cur, "signals")
            has_intents = table_exists(cur, "execution_intents")
            has_trades = table_exists(cur, "trades")

        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            runtime_rows = []
            if has_runtime:
                cur.execute(
                    """
                    select *
                    from runtime_active_universe
                    where symbol = %s
                    order by updated_at desc nulls last
                    limit 20
                    """,
                    (SYMBOL,),
                )
                runtime_rows = list(cur.fetchall())

            bar_rows = []
            if has_bars:
                cols = columns(cur, "market_bars")
                ts_col = first_col(cols, ["ts", "timestamp", "bar_time", "created_at"])
                if ts_col:
                    cur.execute(
                        f"""
                        select
                            symbol,
                            timeframe,
                            count(*) as bars,
                            min({ts_col}) as first_ts,
                            max({ts_col}) as last_ts
                        from market_bars
                        where symbol = %s
                          and {ts_col} >= now() - (%s::text)::interval
                        group by symbol, timeframe
                        order by timeframe
                        """,
                        (SYMBOL, interval),
                    )
                    bar_rows = list(cur.fetchall())

            signal_rows = []
            if has_signals:
                cols = columns(cur, "signals")
                ts_col = first_col(cols, ["created_at", "ts", "timestamp", "signal_time"])
                if ts_col and "symbol" in cols:
                    strategy_expr = "coalesce(strategy, 'UNKNOWN')" if "strategy" in cols else "'UNKNOWN'"
                    reason_expr = "coalesce(signal_class, reason, 'UNKNOWN')" if {"signal_class", "reason"}.issubset(cols) else (
                        "coalesce(signal_class, 'UNKNOWN')" if "signal_class" in cols else (
                            "coalesce(reason, 'UNKNOWN')" if "reason" in cols else "'UNKNOWN'"
                        )
                    )
                    cur.execute(
                        f"""
                        select
                            symbol,
                            {strategy_expr} as strategy,
                            {reason_expr} as reason,
                            count(*) as signals,
                            min({ts_col}) as first_ts,
                            max({ts_col}) as last_ts
                        from signals
                        where symbol = %s
                          and {ts_col} >= now() - (%s::text)::interval
                        group by 1,2,3
                        order by signals desc
                        """,
                        (SYMBOL, interval),
                    )
                    signal_rows = list(cur.fetchall())

            intent_rows = []
            if has_intents:
                cols = columns(cur, "execution_intents")
                ts_col = first_col(cols, ["created_at", "ts", "timestamp"])
                if ts_col and "symbol" in cols:
                    strategy_expr = "coalesce(strategy, 'UNKNOWN')" if "strategy" in cols else "'UNKNOWN'"
                    status_expr = "coalesce(status, 'UNKNOWN')" if "status" in cols else "'UNKNOWN'"
                    source_expr = "coalesce(source, 'UNKNOWN')" if "source" in cols else "'UNKNOWN'"
                    signal_id_expr = "coalesce(signal_id::text, 'NULL')" if "signal_id" in cols else "'NO_SIGNAL_ID_COLUMN'"
                    cur.execute(
                        f"""
                        select
                            symbol,
                            {strategy_expr} as strategy,
                            {status_expr} as status,
                            {source_expr} as source,
                            {signal_id_expr} as signal_id,
                            count(*) as intents,
                            min({ts_col}) as first_ts,
                            max({ts_col}) as last_ts
                        from execution_intents
                        where symbol = %s
                          and {ts_col} >= now() - (%s::text)::interval
                        group by 1,2,3,4,5
                        order by intents desc, last_ts desc
                        """,
                        (SYMBOL, interval),
                    )
                    intent_rows = list(cur.fetchall())

            trade_rows = []
            if has_trades:
                cur.execute(
                    """
                    select
                        symbol,
                        coalesce(strategy, 'UNKNOWN') as strategy,
                        coalesce(timeframe, 'UNKNOWN') as timeframe,
                        coalesce(payload->>'trade_source_class', 'UNCLASSIFIED') as trade_source_class,
                        coalesce(payload->>'source', 'UNKNOWN') as payload_source,
                        count(*) as trades,
                        min(created_at) as first_ts,
                        max(created_at) as last_ts
                    from trades
                    where symbol = %s
                      and created_at >= now() - (%s::text)::interval
                      and coalesce(is_invalid, false) = false
                    group by 1,2,3,4,5
                    order by trades desc
                    """,
                    (SYMBOL, interval),
                )
                trade_rows = list(cur.fetchall())

    print("EQUITY_FLOW_RUNTIME_ROWS")
    for r in runtime_rows:
        print(
            "EQUITY_FLOW_RUNTIME_ROW "
            f"symbol={sval(r.get('symbol'))} "
            f"strategy={sval(r.get('strategy'))} "
            f"timeframe={sval(r.get('timeframe'))} "
            f"is_enabled={int(bool(r.get('is_enabled')))} "
            f"score={sval(r.get('score'), 'NULL')} "
            f"source={sval(r.get('source'), 'NULL')} "
            f"disable_reason={sval(r.get('disable_reason'), 'NONE')}"
        )

    print()
    print("EQUITY_FLOW_BAR_ROWS")
    for r in bar_rows:
        print(
            "EQUITY_FLOW_BAR_ROW "
            f"symbol={r['symbol']} "
            f"timeframe={r['timeframe']} "
            f"bars={r['bars']} "
            f"first_ts={r['first_ts']} "
            f"last_ts={r['last_ts']}"
        )

    print()
    print("EQUITY_FLOW_SIGNAL_ROWS")
    for r in signal_rows:
        print(
            "EQUITY_FLOW_SIGNAL_ROW "
            f"symbol={r['symbol']} "
            f"strategy={r['strategy']} "
            f"reason={r['reason']} "
            f"signals={r['signals']} "
            f"first_ts={r['first_ts']} "
            f"last_ts={r['last_ts']}"
        )

    print()
    print("EQUITY_FLOW_INTENT_ROWS")
    for r in intent_rows:
        print(
            "EQUITY_FLOW_INTENT_ROW "
            f"symbol={r['symbol']} "
            f"strategy={r['strategy']} "
            f"status={r['status']} "
            f"source={r['source']} "
            f"signal_id={r['signal_id']} "
            f"intents={r['intents']} "
            f"first_ts={r['first_ts']} "
            f"last_ts={r['last_ts']}"
        )

    print()
    print("EQUITY_FLOW_TRADE_ROWS")
    for r in trade_rows:
        print(
            "EQUITY_FLOW_TRADE_ROW "
            f"symbol={r['symbol']} "
            f"strategy={r['strategy']} "
            f"timeframe={r['timeframe']} "
            f"trade_source_class={r['trade_source_class']} "
            f"payload_source={r['payload_source']} "
            f"trades={r['trades']} "
            f"first_ts={r['first_ts']} "
            f"last_ts={r['last_ts']}"
        )

    signals_total = sum(int(r["signals"]) for r in signal_rows)
    intents_total = sum(int(r["intents"]) for r in intent_rows)
    trades_total = sum(int(r["trades"]) for r in trade_rows)
    clean_trades_total = sum(int(r["trades"]) for r in trade_rows if r["trade_source_class"] == "RUNTIME_OR_PAPER_CLEAN_ENOUGH")

    print()
    print("EQUITY_SIGNAL_TO_INTENT_FLOW_AUDIT_SUMMARY")
    print(f"runtime_rows={len(runtime_rows)}")
    print(f"bar_groups={len(bar_rows)}")
    print(f"signals_total={signals_total}")
    print(f"execution_intents_total={intents_total}")
    print(f"trades_total={trades_total}")
    print(f"clean_trades_total={clean_trades_total}")
    print("db_update=0")
    print("runtime_changes_required=0")
    print("execution_changes_required=0")
    print("real_trading_enabled=0")
    print("execution_enabled=0")

    if intents_total > 0 and signals_total == 0:
        print("VERDICT=EQUITY_INTENTS_WITHOUT_SIGNALS")
    elif signals_total > 0 and intents_total == 0:
        print("VERDICT=EQUITY_SIGNALS_WITHOUT_INTENTS")
    elif signals_total == 0 and intents_total == 0 and len(bar_rows) > 0:
        print("VERDICT=EQUITY_BARS_OK_NO_SIGNALS_OR_INTENTS")
    elif clean_trades_total > 0:
        print("VERDICT=EQUITY_FLOW_HAS_CLEAN_TRADES")
    else:
        print("VERDICT=EQUITY_FLOW_REVIEW_REQUIRED")

    print("EQUITY_SIGNAL_TO_INTENT_FLOW_AUDIT_V1_OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
