#!/usr/bin/env python3
from __future__ import annotations

import os
import psycopg2


SEMANTIC_KEYS = [
    "intent_type",
    "position_action",
    "action",
    "order_intent",
    "trade_intent",
    "direction",
    "reduce_only",
    "close_only",
    "open_short",
    "open_long",
    "close_short",
    "close_long",
]


def table_exists(cur, table: str) -> bool:
    cur.execute("select to_regclass(%s) is not null;", (f"public.{table}",))
    return bool(cur.fetchone()[0])


def columns(cur, table: str) -> set[str]:
    cur.execute("""
        select column_name
        from information_schema.columns
        where table_schema='public'
          and table_name=%s
    """, (table,))
    return {r[0] for r in cur.fetchall()}


def print_json_key_audit(cur, *, table: str, json_col: str, symbol_col: str, side_col: str, ts_col: str | None) -> None:
    key_checks = " OR ".join([f"{json_col} ? '{k}'" for k in SEMANTIC_KEYS])

    cur.execute(f"""
        select
            {side_col} as side,
            count(*) as rows,
            count(*) filter (where {key_checks}) as semantic_rows
        from {table}
        where {symbol_col} in ('BRM6@RTSX','BRN6@RTSX')
        group by {side_col}
        order by {side_col};
    """)

    for side, rows, semantic_rows in cur.fetchall():
        print(
            f"JSON_SEMANTIC_SUMMARY_ROW table={table} side={side} "
            f"rows={rows} semantic_rows={semantic_rows}"
        )

    print(f"{table.upper()}_SEMANTIC_KEY_COUNTS")
    for key in SEMANTIC_KEYS:
        cur.execute(f"""
            select
                count(*) as rows
            from {table}
            where {symbol_col} in ('BRM6@RTSX','BRN6@RTSX')
              and {json_col} ? %s;
        """, (key,))
        rows = int(cur.fetchone()[0] or 0)
        print(f"KEY_ROW table={table} key={key} rows={rows}")

    if ts_col:
        cur.execute(f"""
            select
                {symbol_col} as symbol,
                {side_col} as side,
                {json_col}::text as payload_text
            from {table}
            where {symbol_col} in ('BRM6@RTSX','BRN6@RTSX')
            order by {ts_col} desc
            limit 20;
        """)
    else:
        cur.execute(f"""
            select
                {symbol_col} as symbol,
                {side_col} as side,
                {json_col}::text as payload_text
            from {table}
            where {symbol_col} in ('BRM6@RTSX','BRN6@RTSX')
            limit 20;
        """)

    print(f"{table.upper()}_PAYLOAD_SAMPLE")
    for symbol, side, payload_text in cur.fetchall():
        compact = str(payload_text or "").replace("\n", " ")[:600]
        print(f"PAYLOAD_SAMPLE_ROW table={table} symbol={symbol} side={side} payload={compact}")


def main() -> None:
    dsn = os.environ["DATABASE_URL"]

    print("=== BR SIGNAL INTENT SEMANTICS AUDIT V1 ===")
    print("mode=research_only")
    print("execution=disabled")
    print("goal=detect_explicit_OPEN_CLOSE_semantics_for_BR_BUY_SELL")
    print()

    semantic_tables_with_rows = 0
    total_semantic_rows = 0

    with psycopg2.connect(dsn) as conn:
        with conn.cursor() as cur:
            print("TABLE_CHECK")
            for table in ("signals", "execution_intents", "orders", "trades"):
                print(f"TABLE_ROW table={table} exists={int(table_exists(cur, table))}")
            print()

            if table_exists(cur, "signals"):
                sig_cols = columns(cur, "signals")
                print("SIGNALS_AUDIT")
                print("SIGNALS_COLUMNS=" + ",".join(sorted(sig_cols)))

                if {"symbol", "side", "payload"}.issubset(sig_cols):
                    print_json_key_audit(
                        cur,
                        table="signals",
                        json_col="payload",
                        symbol_col="symbol",
                        side_col="side",
                        ts_col="created_at" if "created_at" in sig_cols else ("ts" if "ts" in sig_cols else None),
                    )

                    cur.execute("""
                        select count(*)
                        from signals
                        where symbol in ('BRM6@RTSX','BRN6@RTSX')
                          and (
                               payload ? 'intent_type'
                            or payload ? 'position_action'
                            or payload ? 'action'
                            or payload ? 'order_intent'
                            or payload ? 'trade_intent'
                            or payload ? 'reduce_only'
                            or payload ? 'open_short'
                            or payload ? 'close_long'
                          );
                    """)
                    rows = int(cur.fetchone()[0] or 0)
                    semantic_tables_with_rows += int(rows > 0)
                    total_semantic_rows += rows
                else:
                    print("SIGNALS_REQUIRED_COLUMNS_MISSING=1")
                print()

            if table_exists(cur, "execution_intents"):
                intent_cols = columns(cur, "execution_intents")
                print("EXECUTION_INTENTS_AUDIT")
                print("EXECUTION_INTENTS_COLUMNS=" + ",".join(sorted(intent_cols)))

                if {"symbol", "side", "raw_json"}.issubset(intent_cols):
                    print_json_key_audit(
                        cur,
                        table="execution_intents",
                        json_col="raw_json",
                        symbol_col="symbol",
                        side_col="side",
                        ts_col="created_at" if "created_at" in intent_cols else ("updated_at" if "updated_at" in intent_cols else None),
                    )

                    cur.execute("""
                        select count(*)
                        from execution_intents
                        where symbol in ('BRM6@RTSX','BRN6@RTSX')
                          and (
                               raw_json ? 'intent_type'
                            or raw_json ? 'position_action'
                            or raw_json ? 'action'
                            or raw_json ? 'order_intent'
                            or raw_json ? 'trade_intent'
                            or raw_json ? 'reduce_only'
                            or raw_json ? 'open_short'
                            or raw_json ? 'close_long'
                          );
                    """)
                    rows = int(cur.fetchone()[0] or 0)
                    semantic_tables_with_rows += int(rows > 0)
                    total_semantic_rows += rows
                else:
                    print("EXECUTION_INTENTS_REQUIRED_COLUMNS_MISSING=1")
                print()

            if table_exists(cur, "orders"):
                order_cols = columns(cur, "orders")
                print("ORDERS_AUDIT")
                print("ORDERS_COLUMNS=" + ",".join(sorted(order_cols)))

                if {"symbol", "side", "raw_json"}.issubset(order_cols):
                    print_json_key_audit(
                        cur,
                        table="orders",
                        json_col="raw_json",
                        symbol_col="symbol",
                        side_col="side",
                        ts_col="created_ts" if "created_ts" in order_cols else ("updated_ts" if "updated_ts" in order_cols else None),
                    )
                else:
                    print("ORDERS_REQUIRED_COLUMNS_MISSING=1")
                print()

            if table_exists(cur, "trades"):
                trade_cols = columns(cur, "trades")
                print("TRADES_AUDIT")
                print("TRADES_COLUMNS=" + ",".join(sorted(trade_cols)))

                if {"symbol", "side", "payload"}.issubset(trade_cols):
                    print_json_key_audit(
                        cur,
                        table="trades",
                        json_col="payload",
                        symbol_col="symbol",
                        side_col="side",
                        ts_col="ts" if "ts" in trade_cols else ("created_at" if "created_at" in trade_cols else None),
                    )
                else:
                    print("TRADES_REQUIRED_COLUMNS_MISSING=1")
                print()

            print("POSITION_SEMANTICS_INFERENCE")
            cur.execute("""
                with x as (
                    select
                        symbol,
                        ts,
                        id,
                        side,
                        qty,
                        sum(case when side='BUY' then qty else -qty end)
                          over (
                            partition by symbol
                            order by ts, id
                            rows between unbounded preceding and 1 preceding
                          ) as position_before,
                        sum(case when side='BUY' then qty else -qty end)
                          over (
                            partition by symbol
                            order by ts, id
                            rows between unbounded preceding and current row
                          ) as position_after
                    from trades
                    where symbol in ('BRM6@RTSX','BRN6@RTSX')
                      and trade_source='paper'
                      and coalesce(is_invalid,false)=false
                )
                select
                    symbol,
                    side,
                    count(*) as rows,
                    count(*) filter (where side='BUY' and coalesce(position_before,0) >= 0) as inferred_open_or_add_long,
                    count(*) filter (where side='SELL' and coalesce(position_before,0) > 0) as inferred_close_or_reduce_long,
                    count(*) filter (where side='SELL' and coalesce(position_before,0) <= 0) as inferred_open_or_add_short,
                    count(*) filter (where side='BUY' and coalesce(position_before,0) < 0) as inferred_close_or_reduce_short,
                    count(*) filter (where position_after < 0) as resulted_short_position
                from x
                group by symbol, side
                order by symbol, side;
            """)
            resulted_short_total = 0
            for row in cur.fetchall():
                (
                    symbol,
                    side,
                    rows,
                    open_long,
                    close_long,
                    open_short,
                    close_short,
                    resulted_short,
                ) = row
                resulted_short_total += int(resulted_short or 0)
                print(
                    f"INFERENCE_ROW symbol={symbol} side={side} rows={rows} "
                    f"inferred_open_or_add_long={open_long} "
                    f"inferred_close_or_reduce_long={close_long} "
                    f"inferred_open_or_add_short={open_short} "
                    f"inferred_close_or_reduce_short={close_short} "
                    f"resulted_short_position={resulted_short}"
                )

    print()
    print(f"TOTAL_EXPLICIT_SEMANTIC_ROWS={total_semantic_rows}")
    print(f"SEMANTIC_TABLES_WITH_ROWS={semantic_tables_with_rows}")
    print(f"RESULTED_SHORT_POSITION_ROWS={resulted_short_total}")
    print()

    if total_semantic_rows > 0:
        print("VERDICT=EXPLICIT_INTENT_SEMANTICS_FOUND")
    elif resulted_short_total > 0:
        print("VERDICT=SEMANTICS_INFERRED_FROM_POSITION_ONLY")
    else:
        print("VERDICT=NO_EXPLICIT_OPEN_CLOSE_SEMANTICS")


if __name__ == "__main__":
    main()
