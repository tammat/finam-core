#!/usr/bin/env python3

import os
import psycopg2
import psycopg2.extras

SOURCE="closed_trade_engine_v1_1"

conn = psycopg2.connect(os.environ["DATABASE_URL"])

with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:

    print("=== CLOSED TRADES DUPLICATE AUDIT V1 ===")
    print("mode=research_only")
    print("execution=disabled")
    print("runtime_changed=0")
    print(f"source={SOURCE}")
    print()

    cur.execute("""
        SELECT
            symbol,
            side,
            entry_ts,
            exit_ts,
            entry_price,
            exit_price,
            qty,
            count(*) AS cnt
        FROM closed_trades
        WHERE source=%s
        GROUP BY
            symbol,
            side,
            entry_ts,
            exit_ts,
            entry_price,
            exit_price,
            qty
        HAVING count(*) > 1
        ORDER BY cnt DESC
    """,(SOURCE,))

    rows = cur.fetchall()

    total_dup_rows = 0
    total_dup_groups = len(rows)

    print("DUPLICATE_GROUPS")

    for r in rows[:100]:
        total_dup_rows += int(r["cnt"])

        print(
            f"DUPLICATE_ROW "
            f"symbol={r['symbol']} "
            f"side={r['side']} "
            f"qty={r['qty']} "
            f"entry_ts={r['entry_ts']} "
            f"exit_ts={r['exit_ts']} "
            f"copies={r['cnt']}"
        )

    print()

    cur.execute("""
        SELECT
            left(symbol,2) root,
            count(*) total_rows
        FROM closed_trades
        WHERE source=%s
        GROUP BY 1
        ORDER BY 1
    """,(SOURCE,))

    roots = cur.fetchall()

    print("ROOT_TOTALS")

    for r in roots:
        print(
            f"ROOT_ROW "
            f"root={r['root']} "
            f"rows={r['total_rows']}"
        )

    print()

    print("SUMMARY")
    print(f"DUPLICATE_GROUPS={total_dup_groups}")
    print(f"DUPLICATE_ROWS={total_dup_rows}")

    if total_dup_groups == 0:
        verdict = "NO_DUPLICATES"
    else:
        verdict = "DUPLICATES_FOUND"

    print(f"VERDICT={verdict}")
    print("CLOSED_TRADES_DUPLICATE_AUDIT_V1_OK")

conn.close()
