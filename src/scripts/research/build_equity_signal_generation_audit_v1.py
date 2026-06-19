#!/usr/bin/env python3
from __future__ import annotations

import os
from typing import Any

import psycopg2
import psycopg2.extras


# Русский комментарий:
# EQUITY_SIGNAL_GENERATION_AUDIT_V1
# Read-only аудит генерации equity signals.
# Фокус: почему SBER@MISX / VOLATILITY_BREAKOUT_EQUITY / M5
# имеет runtime row и market_bars, но не создаёт signals.


SYMBOL = os.getenv("EQUITY_FLOW_SYMBOL", "SBER@MISX")
EXPECTED_STRATEGY = os.getenv("EQUITY_EXPECTED_STRATEGY", "VOLATILITY_BREAKOUT_EQUITY")
TIMEFRAME = os.getenv("EQUITY_TIMEFRAME", "M5")
LOOKBACK_DAYS = int(os.getenv("EQUITY_SIGNAL_GEN_LOOKBACK_DAYS", "30"))


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

    print("=== EQUITY SIGNAL GENERATION AUDIT V1 ===")
    print("mode=read_only")
    print("runtime_allow=0")
    print("execution_enabled=0")
    print("real_trading_enabled=0")
    print("db_update=0")
    print(f"symbol={SYMBOL}")
    print(f"expected_strategy={EXPECTED_STRATEGY}")
    print(f"timeframe={TIMEFRAME}")
    print(f"lookback_days={LOOKBACK_DAYS}")
    print()

    with psycopg2.connect(dsn) as conn:
        with conn.cursor() as cur:
            has_runtime = table_exists(cur, "runtime_active_universe")
            has_bars = table_exists(cur, "market_bars")
            has_signals = table_exists(cur, "signals")

            candidate_tables = [
                "features",
                "signal_features",
                "strategy_features",
                "runtime_guard_pre_signal_block_audit_v1",
                "runtime_signal_block_audit_v1",
                "signal_quality_events",
                "risk_events",
            ]
            existing_tables = [t for t in candidate_tables if table_exists(cur, t)]

        runtime_rows = []
        bar_rows = []
        signal_rows = []
        feature_audit_rows = []
        block_rows = []
        risk_rows = []

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
                          and timeframe = %s
                          and {ts_col} >= now() - (%s::text)::interval
                        group by symbol, timeframe
                        """,
                        (SYMBOL, TIMEFRAME, interval),
                    )
                    bar_rows = list(cur.fetchall())

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

            for table in existing_tables:
                cols = columns(cur, table)
                ts_col = first_col(cols, ["created_at", "ts", "timestamp", "updated_at"])
                if not ts_col or "symbol" not in cols:
                    continue

                strategy_expr = "coalesce(strategy, 'UNKNOWN')" if "strategy" in cols else "'UNKNOWN'"
                reason_expr = (
                    "coalesce(reason, block_reason, event_type, status, 'UNKNOWN')"
                    if {"reason", "block_reason", "event_type", "status"}.intersection(cols)
                    else "'UNKNOWN'"
                )

                # Русский комментарий:
                # Для разных audit-таблиц схемы могут различаться.
                # Поэтому читаем только безопасный минимум.
                available_reason_parts = []
                for c in ["reason", "block_reason", "event_type", "status"]:
                    if c in cols:
                        available_reason_parts.append(c)
                reason_expr = "coalesce(" + ",".join(available_reason_parts + ["'UNKNOWN'"]) + ")" if available_reason_parts else "'UNKNOWN'"

                cur.execute(
                    f"""
                    select
                        %s as table_name,
                        symbol,
                        {strategy_expr} as strategy,
                        {reason_expr} as reason,
                        count(*) as rows,
                        min({ts_col}) as first_ts,
                        max({ts_col}) as last_ts
                    from {table}
                    where symbol = %s
                      and {ts_col} >= now() - (%s::text)::interval
                    group by 1,2,3,4
                    order by rows desc
                    limit 20
                    """,
                    (table, SYMBOL, interval),
                )
                audit_rows = list(cur.fetchall())

                if "risk" in table:
                    risk_rows.extend(audit_rows)
                elif "block" in table or "guard" in table:
                    block_rows.extend(audit_rows)
                else:
                    feature_audit_rows.extend(audit_rows)

    print("EQUITY_SIGNAL_GEN_RUNTIME_ROWS")
    for r in runtime_rows:
        print(
            "EQUITY_SIGNAL_GEN_RUNTIME_ROW "
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
    print("EQUITY_SIGNAL_GEN_BAR_ROWS")
    for r in bar_rows:
        print(
            "EQUITY_SIGNAL_GEN_BAR_ROW "
            f"symbol={r['symbol']} "
            f"timeframe={r['timeframe']} "
            f"bars={r['bars']} "
            f"first_ts={r['first_ts']} "
            f"last_ts={r['last_ts']}"
        )

    print()
    print("EQUITY_SIGNAL_GEN_SIGNAL_ROWS")
    for r in signal_rows:
        print(
            "EQUITY_SIGNAL_GEN_SIGNAL_ROW "
            f"strategy={r['strategy']} "
            f"reason={r['reason']} "
            f"signals={r['signals']} "
            f"first_ts={r['first_ts']} "
            f"last_ts={r['last_ts']}"
        )

    print()
    print("EQUITY_SIGNAL_GEN_FEATURE_AUDIT_ROWS")
    for r in feature_audit_rows:
        print(
            "EQUITY_SIGNAL_GEN_FEATURE_AUDIT_ROW "
            f"table={r['table_name']} "
            f"symbol={r['symbol']} "
            f"strategy={r['strategy']} "
            f"reason={r['reason']} "
            f"rows={r['rows']} "
            f"first_ts={r['first_ts']} "
            f"last_ts={r['last_ts']}"
        )

    print()
    print("EQUITY_SIGNAL_GEN_BLOCK_ROWS")
    for r in block_rows:
        print(
            "EQUITY_SIGNAL_GEN_BLOCK_ROW "
            f"table={r['table_name']} "
            f"symbol={r['symbol']} "
            f"strategy={r['strategy']} "
            f"reason={r['reason']} "
            f"rows={r['rows']} "
            f"first_ts={r['first_ts']} "
            f"last_ts={r['last_ts']}"
        )

    print()
    print("EQUITY_SIGNAL_GEN_RISK_ROWS")
    for r in risk_rows:
        print(
            "EQUITY_SIGNAL_GEN_RISK_ROW "
            f"table={r['table_name']} "
            f"symbol={r['symbol']} "
            f"strategy={r['strategy']} "
            f"reason={r['reason']} "
            f"rows={r['rows']} "
            f"first_ts={r['first_ts']} "
            f"last_ts={r['last_ts']}"
        )

    runtime_ok = any(
        r["symbol"] == SYMBOL
        and r["strategy"] == EXPECTED_STRATEGY
        and r["timeframe"] == TIMEFRAME
        and bool(r["is_enabled"])
        for r in runtime_rows
    )
    bars_total = sum(int(r["bars"]) for r in bar_rows)
    signals_total = sum(int(r["signals"]) for r in signal_rows)
    feature_audit_total = sum(int(r["rows"]) for r in feature_audit_rows)
    block_total = sum(int(r["rows"]) for r in block_rows)
    risk_total = sum(int(r["rows"]) for r in risk_rows)

    print()
    print("EQUITY_SIGNAL_GENERATION_AUDIT_SUMMARY")
    print(f"runtime_ok={int(runtime_ok)}")
    print(f"bars_total={bars_total}")
    print(f"signals_total={signals_total}")
    print(f"feature_audit_rows={feature_audit_total}")
    print(f"block_rows={block_total}")
    print(f"risk_rows={risk_total}")
    print(f"existing_audit_tables={','.join(existing_tables) if existing_tables else 'NONE'}")
    print("db_update=0")
    print("runtime_changes_required=0")
    print("execution_changes_required=0")
    print("real_trading_enabled=0")
    print("execution_enabled=0")

    if runtime_ok and bars_total > 0 and signals_total == 0 and block_total > 0:
        print("VERDICT=EQUITY_SIGNAL_BLOCKED_BEFORE_EMIT")
    elif runtime_ok and bars_total > 0 and signals_total == 0:
        print("VERDICT=EQUITY_STRATEGY_GENERATES_NO_SIGNALS")
    elif runtime_ok and bars_total == 0:
        print("VERDICT=EQUITY_RUNTIME_ENABLED_NO_BARS")
    elif signals_total > 0:
        print("VERDICT=EQUITY_SIGNALS_EXIST")
    else:
        print("VERDICT=EQUITY_SIGNAL_GENERATION_REVIEW_REQUIRED")

    print("EQUITY_SIGNAL_GENERATION_AUDIT_V1_OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
