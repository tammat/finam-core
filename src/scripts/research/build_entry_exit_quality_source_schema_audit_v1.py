#!/usr/bin/env python3
import os
import psycopg
from psycopg.rows import dict_row

dsn = os.environ["DATABASE_URL"]

print("=== ENTRY_EXIT_QUALITY_SOURCE_SCHEMA_AUDIT_V1 ===")
print("mode=read_only_schema_audit")
print("db_update=0")
print("runtime_changed=0")
print("execution_changed=0")
print("real_trading_enabled=0")

keywords = [
    "pnl", "profit", "loss", "return", "exit", "reason",
    "closed", "cycle", "fill", "commission", "entry", "trade"
]

with psycopg.connect(dsn, row_factory=dict_row) as conn:
    with conn.cursor() as cur:
        cur.execute("""
            select table_name
            from information_schema.tables
            where table_schema='public'
              and table_type='BASE TABLE'
            order by table_name
        """)
        tables = [r["table_name"] for r in cur.fetchall()]

        for table in tables:
            cur.execute("""
                select column_name, data_type
                from information_schema.columns
                where table_schema='public'
                  and table_name=%s
                order by ordinal_position
            """, (table,))
            cols = cur.fetchall()
            matched = [
                c for c in cols
                if any(k in c["column_name"].lower() for k in keywords)
            ]

            if not matched:
                continue

            cur.execute(f"select count(*)::int as n from {table}")
            n = cur.fetchone()["n"]

            print(f"\nTABLE table={table} rows={n}")
            for c in matched:
                print(
                    f"COLUMN table={table} "
                    f"name={c['column_name']} "
                    f"type={c['data_type']}"
                )

print("\nVERDICT=ENTRY_EXIT_QUALITY_SOURCE_SCHEMA_AUDIT_READY")
