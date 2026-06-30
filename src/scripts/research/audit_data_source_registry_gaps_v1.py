#!/usr/bin/env python3
from __future__ import annotations

import os
import psycopg2

DB = os.getenv("DATABASE_URL", "postgresql:///finam_core")

SQL_TABLES = """
SELECT
    n.nspname AS schema_name,
    c.relname AS table_name
FROM pg_class c
JOIN pg_namespace n
  ON n.oid = c.relnamespace
WHERE c.relkind = 'r'
  AND n.nspname NOT IN ('pg_catalog', 'information_schema')
ORDER BY n.nspname, c.relname;
"""

SQL_REGISTRY = """
SELECT
    source_origin,
    domain,
    producer,
    canonical_entity,
    normalization_status
FROM warehouse.data_source_registry_v1
WHERE active=true
ORDER BY source_origin;
"""

def classify_table(schema: str, table: str) -> str | None:
    name = f"{schema}.{table}".lower()

    if table == "market_bars" or table == "market_ticks":
        return "Finam Runtime"

    if "replay" in name:
        return "Replay"

    if "paper" in name:
        return "Paper Trading"

    if any(x in name for x in ["order", "fill", "trade", "position", "portfolio", "execution", "mtm"]):
        return "Runtime Trading"

    if "broker" in name or "finam" in name:
        return "Broker"

    if any(x in name for x in ["strategy", "signal", "candidate", "scorecard", "edge"]):
        return "Strategy"

    if any(x in name for x in ["research", "analytics", "experiment", "model"]):
        return "Research"

    if "feature" in name:
        return "Feature"

    if name.startswith("warehouse.ai_") or "_ai_" in name:
        return "AI"

    if name.startswith("warehouse.normalized_"):
        return "Finam History"

    return None

def main() -> None:
    print("=== DATA_SOURCE_REGISTRY_GAP_AUDIT_V1 ===")

    conn = psycopg2.connect(DB)
    try:
        with conn.cursor() as cur:
            cur.execute(SQL_TABLES)
            tables = cur.fetchall()

            cur.execute(SQL_REGISTRY)
            registry_rows = cur.fetchall()

        registry_sources = {r[0] for r in registry_rows}
        covered = []
        uncovered = []

        observed_sources = set()

        for schema, table in tables:
            source = classify_table(schema, table)

            if source and source in registry_sources:
                covered.append((schema, table, source))
                observed_sources.add(source)
                print(f"COVERED|schema={schema}|table={table}|source_origin={source}")
            else:
                uncovered.append((schema, table))
                print(f"UNCOVERED|schema={schema}|table={table}|reason=NO_REGISTRY_MAPPING")

        orphan_sources = sorted(registry_sources - observed_sources)

        for source in orphan_sources:
            print(f"ORPHAN|source_origin={source}|reason=NO_MATCHING_TABLE_DETECTED")

        print(f"tables_scanned={len(tables)}")
        print(f"covered_tables={len(covered)}")
        print(f"uncovered_tables={len(uncovered)}")
        print(f"orphan_sources={len(orphan_sources)}")
        print("gap_audit=READY")
        print("runtime_changed=0")
        print("execution_changed=0")
        print("orders_changed=0")
        print("fills_changed=0")
        print("micro_live_allowed=0")
        print("VERDICT=DATA_SOURCE_REGISTRY_GAP_AUDIT_V1_READY")
    finally:
        conn.close()

if __name__ == "__main__":
    main()
