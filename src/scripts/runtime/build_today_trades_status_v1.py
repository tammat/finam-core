#!/usr/bin/env python3
from __future__ import annotations

import os
from typing import Any

import psycopg2
import psycopg2.extras


# Русский комментарий:
# TODAY_TRADES_STATUS_V1 — schema-safe read-only отчёт по сегодняшним сделкам.
# Ничего не меняет в БД, runtime, execution и real trading.


def fmt(value: Any) -> str:
    if value is None:
        return "NULL"
    return str(value)


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


def first_existing(cols: set[str], candidates: list[str]) -> str | None:
    for col in candidates:
        if col in cols:
            return col
    return None


def build_summary_sql(cols: set[str]) -> str:
    strategy_expr = (
        "count(*) filter (where coalesce(strategy, '') = '' or strategy in ('UNKNOWN', 'UNKNOWN_STRATEGY'))"
        if "strategy" in cols else
        "0"
    )
    timeframe_expr = (
        "count(*) filter (where coalesce(timeframe, '') = '' or timeframe in ('UNKNOWN', 'UNKNOWN_TIMEFRAME'))"
        if "timeframe" in cols else
        "0"
    )
    continuous_expr = (
        "count(*) filter (where coalesce(continuous_symbol, '') = '')"
        if "continuous_symbol" in cols else
        "0"
    )

    return f"""
    select
        count(*) as trades_today,
        {strategy_expr} as strategy_missing,
        {timeframe_expr} as timeframe_missing,
        {continuous_expr} as continuous_symbol_missing,
        min(created_at) as first_trade,
        max(created_at) as last_trade
    from trades
    where created_at::date = current_date;
    """


def build_by_symbol_sql(cols: set[str]) -> tuple[str, str, str]:
    symbol_col = "symbol" if "symbol" in cols else "null::text"
    strategy_col = "strategy" if "strategy" in cols else "null::text"
    timeframe_col = "timeframe" if "timeframe" in cols else "null::text"
    side_col = "side" if "side" in cols else "null::text"

    pnl_col = first_existing(cols, ["net_pnl", "pnl", "realized_pnl", "profit", "profit_loss"])
    gross_col = first_existing(cols, ["gross_pnl", "gross_profit", "pnl_gross"])

    pnl_expr = f"sum(coalesce({pnl_col}, 0))" if pnl_col else "0::numeric"
    gross_expr = f"sum(coalesce({gross_col}, 0))" if gross_col else "0::numeric"

    sql = f"""
    select
        {symbol_col} as symbol,
        coalesce({strategy_col}, 'UNKNOWN') as strategy,
        coalesce({timeframe_col}, 'UNKNOWN') as timeframe,
        count(*) as trades,
        count(*) filter (where upper(coalesce({side_col}, '')) in ('BUY', 'LONG')) as buy_trades,
        count(*) filter (where upper(coalesce({side_col}, '')) in ('SELL', 'SHORT')) as sell_trades,
        {pnl_expr} as net_pnl,
        {gross_expr} as gross_pnl,
        min(created_at) as first_trade,
        max(created_at) as last_trade
    from trades
    where created_at::date = current_date
    group by symbol, strategy, timeframe
    order by trades desc, symbol, strategy, timeframe;
    """

    return sql, pnl_col or "none", gross_col or "none"


def build_recent_sql(cols: set[str]) -> tuple[str, str, str]:
    symbol_col = "symbol" if "symbol" in cols else "null::text"
    strategy_col = "strategy" if "strategy" in cols else "null::text"
    timeframe_col = "timeframe" if "timeframe" in cols else "null::text"
    side_col = "side" if "side" in cols else "null::text"
    qty_col = first_existing(cols, ["qty", "quantity", "volume"])
    price_col = first_existing(cols, ["price", "fill_price", "entry_price"])

    pnl_col = first_existing(cols, ["net_pnl", "pnl", "realized_pnl", "profit", "profit_loss"])
    gross_col = first_existing(cols, ["gross_pnl", "gross_profit", "pnl_gross"])

    qty_expr = qty_col if qty_col else "null::numeric"
    price_expr = price_col if price_col else "null::numeric"
    pnl_expr = f"coalesce({pnl_col}, 0)" if pnl_col else "0::numeric"
    gross_expr = f"coalesce({gross_col}, 0)" if gross_col else "0::numeric"

    sql = f"""
    select
        created_at,
        {symbol_col} as symbol,
        coalesce({strategy_col}, 'UNKNOWN') as strategy,
        coalesce({timeframe_col}, 'UNKNOWN') as timeframe,
        {side_col} as side,
        {qty_expr} as qty,
        {price_expr} as price,
        {pnl_expr} as net_pnl,
        {gross_expr} as gross_pnl
    from trades
    where created_at::date = current_date
    order by created_at desc
    limit 20;
    """

    return sql, pnl_col or "none", gross_col or "none"


def main() -> int:
    dsn = os.getenv("DATABASE_URL")
    if not dsn:
        raise SystemExit("DATABASE_URL is required")

    print("=== TODAY TRADES STATUS V1 ===")
    print("mode=read_only")
    print("runtime_allow=0")
    print("execution_enabled=0")
    print("real_trading_enabled=0")
    print("db_update=0")
    print()

    with psycopg2.connect(dsn) as conn:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cols = table_columns(cur, "trades")

            summary_sql = build_summary_sql(cols)
            by_symbol_sql, pnl_source, gross_pnl_source = build_by_symbol_sql(cols)
            recent_sql, recent_pnl_source, recent_gross_source = build_recent_sql(cols)

            cur.execute(summary_sql)
            summary = cur.fetchone() or {}

            cur.execute(by_symbol_sql)
            rows = cur.fetchall()

            cur.execute(recent_sql)
            recent = cur.fetchall()

    trades_today = int(summary.get("trades_today") or 0)
    strategy_missing = int(summary.get("strategy_missing") or 0)
    timeframe_missing = int(summary.get("timeframe_missing") or 0)
    continuous_missing = int(summary.get("continuous_symbol_missing") or 0)

    print("TODAY_TRADES_SCHEMA")
    print(f"trades_columns={','.join(sorted(cols))}")
    print(f"pnl_source={pnl_source}")
    print(f"gross_pnl_source={gross_pnl_source}")

    print()
    print("TODAY_TRADES_SUMMARY")
    print(f"trades_today={trades_today}")
    print(f"strategy_missing={strategy_missing}")
    print(f"timeframe_missing={timeframe_missing}")
    print(f"continuous_symbol_missing={continuous_missing}")
    print(f"first_trade={fmt(summary.get('first_trade'))}")
    print(f"last_trade={fmt(summary.get('last_trade'))}")

    print()
    print("TODAY_TRADES_BY_SYMBOL")
    total_net = 0.0
    for row in rows:
        net = float(row.get("net_pnl") or 0.0)
        total_net += net
        print(
            "TODAY_TRADES_SYMBOL_ROW "
            f"symbol={fmt(row.get('symbol'))} "
            f"strategy={fmt(row.get('strategy'))} "
            f"timeframe={fmt(row.get('timeframe'))} "
            f"trades={fmt(row.get('trades'))} "
            f"buy_trades={fmt(row.get('buy_trades'))} "
            f"sell_trades={fmt(row.get('sell_trades'))} "
            f"net_pnl={net:.6f} "
            f"gross_pnl={float(row.get('gross_pnl') or 0.0):.6f} "
            f"first_trade={fmt(row.get('first_trade'))} "
            f"last_trade={fmt(row.get('last_trade'))}"
        )

    print()
    print("TODAY_TRADES_RECENT")
    for row in recent:
        print(
            "TODAY_TRADES_RECENT_ROW "
            f"created_at={fmt(row.get('created_at'))} "
            f"symbol={fmt(row.get('symbol'))} "
            f"strategy={fmt(row.get('strategy'))} "
            f"timeframe={fmt(row.get('timeframe'))} "
            f"side={fmt(row.get('side'))} "
            f"qty={fmt(row.get('qty'))} "
            f"price={fmt(row.get('price'))} "
            f"net_pnl={float(row.get('net_pnl') or 0.0):.6f} "
            f"gross_pnl={float(row.get('gross_pnl') or 0.0):.6f}"
        )

    print()
    print("TODAY_TRADES_STATUS_SUMMARY")
    print(f"symbols={len(rows)}")
    print(f"total_net_pnl={total_net:.6f}")
    print(f"context_clean={1 if strategy_missing == 0 and timeframe_missing == 0 and continuous_missing == 0 else 0}")
    print("db_update=0")

    if trades_today == 0:
        print("VERDICT=TODAY_TRADES_NONE")
    elif strategy_missing == 0 and timeframe_missing == 0 and continuous_missing == 0:
        print("VERDICT=TODAY_TRADES_CONTEXT_CLEAN")
    else:
        print("VERDICT=TODAY_TRADES_CONTEXT_HAS_GAPS")

    print("TODAY_TRADES_STATUS_V1_OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
