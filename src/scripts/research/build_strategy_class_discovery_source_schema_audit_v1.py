#!/usr/bin/env python3
import os
import psycopg
from psycopg.rows import dict_row

dsn = os.environ["DATABASE_URL"]

tables = [
    "analytics_futures_rs_bottom_paper_observation_v1",
    "analytics_rs_bottom_runtime_dry_run_v1",
    "trades",
    "signals",
    "execution_intents",
    "signal_features",
    "analytics_trade_source_classification_v1",
]

print("=== STRATEGY_CLASS_DISCOVERY_SOURCE_SCHEMA_AUDIT_V1 ===")
print("mode=read_only")
print("db_update=0")
print("runtime_changed=0")
print("execution_changed=0")
print("real_trading_enabled=0")

with psycopg.connect(dsn, row_factory=dict_row) as conn:
    with conn.cursor() as cur:
        for table in tables:
            cur.execute("""
                select exists (
                    select 1 from information_schema.tables
                    where table_schema='public' and table_name=%s
                ) as exists
            """, (table,))
            exists = cur.fetchone()["exists"]
            print(f"\nTABLE table={table} exists={1 if exists else 0}")
            if not exists:
                continue

            cur.execute("""
                select column_name, data_type
                from information_schema.columns
                where table_schema='public' and table_name=%s
                order by ordinal_position
            """, (table,))
            cols = cur.fetchall()
            for c in cols:
                name = c["column_name"]
                if any(k in name.lower() for k in [
                    "strategy", "signal", "reason", "class", "payload", "json",
                    "feature", "source", "return", "pnl", "status", "symbol"
                ]):
                    print(f"COLUMN table={table} name={name} type={c['data_type']}")

            cur.execute(f"select count(*)::int as n from {table}")
            print(f"ROWCOUNT table={table} rows={cur.fetchone()['n']}")

print("\nVERDICT=STRATEGY_CLASS_DISCOVERY_SOURCE_SCHEMA_AUDIT_READY")
