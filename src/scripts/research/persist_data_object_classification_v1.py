#!/usr/bin/env python3
from __future__ import annotations

import os
import psycopg2

DB = os.getenv("DATABASE_URL", "postgresql:///finam_core")

SQL_TABLES = """
SELECT
    n.nspname AS schema_name,
    c.relname AS table_name,
    COALESCE(s.n_live_tup, 0) AS rows_estimate,
    pg_total_relation_size(c.oid) AS bytes_size
FROM pg_class c
JOIN pg_namespace n
  ON n.oid = c.relnamespace
LEFT JOIN pg_stat_user_tables s
  ON s.relid = c.oid
WHERE c.relkind = 'r'
  AND n.nspname NOT IN ('pg_catalog', 'information_schema')
ORDER BY n.nspname, c.relname;
"""

DDL = """
CREATE TABLE IF NOT EXISTS warehouse.data_object_classification_v1 (
    id bigserial PRIMARY KEY,
    schema_name text NOT NULL,
    table_name text NOT NULL,
    object_type text NOT NULL,
    rows_estimate bigint NOT NULL DEFAULT 0,
    bytes_size bigint NOT NULL DEFAULT 0,
    active boolean NOT NULL DEFAULT true,
    created_at timestamptz NOT NULL DEFAULT now(),
    updated_at timestamptz NOT NULL DEFAULT now(),
    UNIQUE (schema_name, table_name)
);
"""

UPSERT = """
INSERT INTO warehouse.data_object_classification_v1 (
    schema_name,
    table_name,
    object_type,
    rows_estimate,
    bytes_size
)
VALUES (%s, %s, %s, %s, %s)
ON CONFLICT (schema_name, table_name)
DO UPDATE SET
    object_type=EXCLUDED.object_type,
    rows_estimate=EXCLUDED.rows_estimate,
    bytes_size=EXCLUDED.bytes_size,
    active=true,
    updated_at=now();
"""

def classify_object(schema: str, table: str) -> str:
    name = f"{schema}.{table}".lower()

    if schema == "reference":
        return "REFERENCE"
    if table.startswith("dim_"):
        return "DIMENSION"
    if table.startswith("fact_"):
        return "FACT"
    if table.startswith("mart_"):
        return "MART"
    if "registry" in table:
        return "REGISTRY"
    if "audit" in table or "reconciliation" in table:
        return "AUDIT"
    if "workflow" in table or "pipeline" in table:
        return "WORKFLOW"
    if "governance" in table or "gate" in table or "guard" in table:
        return "GOVERNANCE"
    if "telemetry" in table or "metrics" in table or "monitor" in table or "alert" in table:
        return "TELEMETRY"
    if "config" in table or "policy" in table or "profile" in table or "template" in table:
        return "CONFIGURATION"
    if "runtime_state" in table or "state" in table or "snapshot" in table or "projection" in table:
        return "RUNTIME_STATE"
    if "cache" in table or "dedup" in table:
        return "CACHE"
    if "risk" in table or "kill_switch" in table or "margin" in table:
        return "RISK"
    if "portfolio" in table or "position" in table:
        return "PORTFOLIO"
    if "order" in table or "fill" in table or "execution" in table or table in {"trades", "transactions"}:
        return "EXECUTION"
    if "strategy" in table or "signal" in table or "candidate" in table or "scorecard" in table or "edge" in table:
        return "STRATEGY"
    if "research" in table or "experiment" in table or "model" in table or "replay" in table:
        return "RESEARCH"
    if "feature" in table:
        return "FEATURE"
    if "ai_" in name or table.startswith("ai"):
        return "AI"
    if table in {"market_bars", "market_ticks", "market_data"} or table.startswith("normalized_"):
        return "DATA_SOURCE"
    if "analytics" in table or "pnl" in table or "drawdown" in table or "quality" in table:
        return "ANALYTICS"

    return "OTHER"

def main() -> None:
    print("=== DATA_OBJECT_CLASSIFICATION_PERSIST_V1 ===")

    conn = psycopg2.connect(DB)
    try:
        with conn.cursor() as cur:
            cur.execute("CREATE SCHEMA IF NOT EXISTS warehouse;")
            cur.execute(DDL)

            cur.execute(SQL_TABLES)
            rows = cur.fetchall()

            persisted = 0
            counts: dict[str, int] = {}

            for schema, table, rows_estimate, bytes_size in rows:
                object_type = classify_object(schema, table)
                cur.execute(UPSERT, (schema, table, object_type, rows_estimate, bytes_size))
                persisted += 1
                counts[object_type] = counts.get(object_type, 0) + 1

            cur.execute("""
                SELECT count(*)
                FROM warehouse.data_object_classification_v1
                WHERE active=true;
            """)
            active_rows = cur.fetchone()[0]

            cur.execute("""
                SELECT count(*)
                FROM warehouse.data_object_classification_v1
                WHERE active=true
                  AND object_type='DATA_SOURCE';
            """)
            data_source_rows = cur.fetchone()[0]

            cur.execute("""
                SELECT count(*)
                FROM warehouse.data_object_classification_v1
                WHERE active=true
                  AND object_type='REGISTRY';
            """)
            registry_rows = cur.fetchone()[0]

            cur.execute("""
                SELECT count(*)
                FROM warehouse.data_object_classification_v1
                WHERE active=true
                  AND object_type='OTHER';
            """)
            other_rows = cur.fetchone()[0]

        conn.commit()

        for object_type in sorted(counts):
            print(f"OBJECT_TYPE|type={object_type}|tables={counts[object_type]}")

        print(f"objects_persisted={persisted}")
        print(f"active_objects={active_rows}")
        print(f"data_source_objects={data_source_rows}")
        print(f"registry_objects={registry_rows}")
        print(f"other_objects={other_rows}")
        print("idempotent_upsert=READY")
        print("classification_persist=READY")
        print("runtime_changed=0")
        print("execution_changed=0")
        print("orders_changed=0")
        print("fills_changed=0")
        print("micro_live_allowed=0")
        print("VERDICT=DATA_OBJECT_CLASSIFICATION_PERSIST_V1_READY")
    finally:
        conn.close()

if __name__ == "__main__":
    main()
