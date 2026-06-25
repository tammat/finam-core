#!/usr/bin/env python3

import os
import psycopg2


CANDIDATE_TABLES = [
    "trades",
    "paper_trades",
    "execution_fills",
    "fills",
    "broker_order_snapshots",
    "analytics_trade_facts_v1",
    "trade_facts",
]


def main() -> int:
    print("=== TRADE_FACTS_SOURCE_DISCOVERY_V1 ===")
    print("mode=discovery_read_only")
    print("db_update=0")
    print("runtime_changed=0")
    print("execution_changed=0")
    print("real_trading_enabled=0")
    print("orders_sent=0")

    db = os.environ.get("DATABASE_URL", "")
    if not db:
        print("ERROR=DATABASE_URL_NOT_SET")
        return 2
    if db.startswith("sqlite"):
        print("ERROR=SQLITE_FORBIDDEN")
        return 2

    with psycopg2.connect(db) as conn:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT table_schema, table_name
                FROM information_schema.tables
                WHERE table_schema NOT IN ('pg_catalog', 'information_schema')
                ORDER BY table_schema, table_name;
            """)
            tables = cur.fetchall()

            print("\nTABLE_DISCOVERY")
            candidates = []

            for schema, table in tables:
                full = f"{schema}.{table}"
                is_candidate = (
                    table in CANDIDATE_TABLES
                    or "trade" in table
                    or "fill" in table
                    or "order" in table
                )

                if is_candidate:
                    candidates.append((schema, table))
                    cur.execute("""
                        SELECT column_name
                        FROM information_schema.columns
                        WHERE table_schema=%s AND table_name=%s
                        ORDER BY ordinal_position;
                    """, (schema, table))
                    cols = [r[0] for r in cur.fetchall()]
                    print(f"CANDIDATE_TABLE name={full} columns={','.join(cols)}")

            print("\nSUMMARY")
            print(f"candidate_tables={len(candidates)}")
            print("research_trade_facts_exists=" + str(any(s == "research" and t == "trade_facts" for s, t in candidates)).lower())

    print("\nNEXT_STEPS")
    print("next=TRADE_FACTS_CANONICAL_SOURCE_PLAN_V1")

    print("\nVERDICT=TRADE_FACTS_SOURCE_DISCOVERY_READY")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
