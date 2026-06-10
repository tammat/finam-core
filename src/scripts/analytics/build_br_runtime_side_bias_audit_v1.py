#!/usr/bin/env python3
from __future__ import annotations

import os
import psycopg2
import psycopg2.extras

DATABASE_URL = os.environ["DATABASE_URL"]

BR_SYMBOLS = ["BRM6@RTSX", "BRN6@RTSX"]

SQL_CLOSED = """
SELECT
    symbol,
    COALESCE(side, 'UNKNOWN') AS side,
    COUNT(*) AS rows,
    ROUND(COALESCE(SUM(net_pnl),0)::numeric,6) AS net_pnl,
    ROUND(COALESCE(AVG(net_pnl),0)::numeric,6) AS expectancy
FROM closed_trades
WHERE symbol = ANY(%s)
GROUP BY symbol, COALESCE(side, 'UNKNOWN')
ORDER BY symbol, side;
"""

CANDIDATE_TABLES = [
    "signals",
    "signal_log",
    "strategy_signals",
    "runtime_signals",
    "raw_intents",
    "signal_intents",
    "order_intents",
    "risk_decisions",
    "trades",
]

def table_exists(cur, table: str) -> bool:
    cur.execute(
        """
        SELECT EXISTS (
            SELECT 1
            FROM information_schema.tables
            WHERE table_schema='public'
              AND table_name=%s
        );
        """,
        (table,),
    )
    return bool(cur.fetchone()["exists"])

def columns(cur, table: str) -> set[str]:
    cur.execute(
        """
        SELECT column_name
        FROM information_schema.columns
        WHERE table_schema='public'
          AND table_name=%s;
        """,
        (table,),
    )
    return {r["column_name"] for r in cur.fetchall()}

def side_column(cols: set[str]) -> str | None:
    for c in ["side", "direction", "action", "signal_side", "order_side"]:
        if c in cols:
            return c
    return None

def symbol_column(cols: set[str]) -> str | None:
    for c in ["symbol", "instrument", "ticker"]:
        if c in cols:
            return c
    return None

def main() -> None:
    print("=== BR RUNTIME SIDE BIAS AUDIT V1 ===")
    print("mode=research_only")
    print("execution=disabled")
    print("runtime_changed=0")
    print("symbols=BRM6@RTSX,BRN6@RTSX")
    print()

    with psycopg2.connect(DATABASE_URL) as conn:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:

            print("CLOSED_TRADE_SIDE_ROWS")
            cur.execute(SQL_CLOSED, (BR_SYMBOLS,))
            closed_rows = cur.fetchall()
            for r in closed_rows:
                print(
                    "CLOSED_SIDE_ROW "
                    f"symbol={r['symbol']} "
                    f"side={r['side']} "
                    f"rows={r['rows']} "
                    f"net_pnl={r['net_pnl']} "
                    f"expectancy={r['expectancy']}"
                )

            print()
            print("LAYER_SIDE_ROWS")

            found_layers = 0
            short_like_rows = 0
            long_like_rows = 0

            for table in CANDIDATE_TABLES:
                if not table_exists(cur, table):
                    print(f"LAYER_ROW table={table} status=TABLE_MISSING")
                    continue

                cols = columns(cur, table)
                sc = symbol_column(cols)
                dc = side_column(cols)

                if not sc or not dc:
                    print(
                        "LAYER_ROW "
                        f"table={table} "
                        f"status=NO_SYMBOL_OR_SIDE_COLUMN "
                        f"symbol_column={sc} "
                        f"side_column={dc}"
                    )
                    continue

                found_layers += 1

                sql = f"""
                SELECT
                    {sc}::text AS symbol,
                    COALESCE({dc}::text, 'UNKNOWN') AS side,
                    COUNT(*) AS rows
                FROM {table}
                WHERE {sc}::text = ANY(%s)
                GROUP BY {sc}::text, COALESCE({dc}::text, 'UNKNOWN')
                ORDER BY symbol, side;
                """
                try:
                    cur.execute(sql, (BR_SYMBOLS,))
                    rows = cur.fetchall()
                except Exception as e:
                    print(f"LAYER_ROW table={table} status=QUERY_FAILED error={type(e).__name__}")
                    conn.rollback()
                    continue

                if not rows:
                    print(f"LAYER_ROW table={table} status=NO_BR_ROWS")
                    continue

                for r in rows:
                    side = str(r["side"]).upper()
                    count = int(r["rows"] or 0)

                    if side in {"SELL", "SHORT", "S"}:
                        short_like_rows += count
                    if side in {"BUY", "LONG", "B"}:
                        long_like_rows += count

                    print(
                        "LAYER_SIDE_ROW "
                        f"table={table} "
                        f"symbol={r['symbol']} "
                        f"side={r['side']} "
                        f"rows={count}"
                    )

            print()
            print("AUDIT_SUMMARY")
            print(
                "SIDE_BIAS_ROW "
                f"layers_with_side={found_layers} "
                f"long_like_rows={long_like_rows} "
                f"short_like_rows={short_like_rows}"
            )

            if short_like_rows == 0 and long_like_rows > 0:
                verdict = "BR_SHORT_SIDE_MISSING_IN_RUNTIME"
            elif short_like_rows > 0 and long_like_rows > 0:
                verdict = "BR_BOTH_SIDES_PRESENT_UPSTREAM"
            elif long_like_rows == 0 and short_like_rows == 0:
                verdict = "BR_SIDE_DATA_NOT_FOUND"
            else:
                verdict = "BR_SIDE_BIAS_INCONCLUSIVE"

            print(f"VERDICT={verdict}")
            print("BR_RUNTIME_SIDE_BIAS_AUDIT_V1_OK")

if __name__ == "__main__":
    main()
