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

OBJECT_TYPES = [
    "DATA_SOURCE",
    "REFERENCE",
    "CONFIGURATION",
    "GOVERNANCE",
    "WORKFLOW",
    "TELEMETRY",
    "RUNTIME_STATE",
    "CACHE",
    "ANALYTICS",
    "AUDIT",
    "DIMENSION",
    "FACT",
    "MART",
    "REGISTRY",
    "EXECUTION",
    "PORTFOLIO",
    "RISK",
    "STRATEGY",
    "RESEARCH",
    "FEATURE",
    "AI",
    "OTHER",
]

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
    print("=== DATA_OBJECT_CLASSIFICATION_V1 ===")

    conn = psycopg2.connect(DB)

    try:
        with conn.cursor() as cur:
            cur.execute(SQL_TABLES)
            rows = cur.fetchall()

        counts: dict[str, int] = {}
        other_rows = []

        for schema, table, rows_estimate, bytes_size in rows:
            object_type = classify_object(schema, table)
            counts[object_type] = counts.get(object_type, 0) + 1

            if object_type == "OTHER":
                other_rows.append((schema, table))

            print(
                "OBJECT"
                f"|schema={schema}"
                f"|table={table}"
                f"|object_type={object_type}"
                f"|rows={rows_estimate}"
                f"|bytes={bytes_size}"
            )

        for object_type in sorted(counts):
            print(f"OBJECT_TYPE|type={object_type}|tables={counts[object_type]}")

        print(f"tables_scanned={len(rows)}")
        print(f"object_types={len(counts)}")
        print(f"other_tables={len(other_rows)}")
        print("classification=READY")
        print("runtime_changed=0")
        print("execution_changed=0")
        print("orders_changed=0")
        print("fills_changed=0")
        print("micro_live_allowed=0")
        print("VERDICT=DATA_OBJECT_CLASSIFICATION_V1_READY")

    finally:
        conn.close()

if __name__ == "__main__":
    main()
