#!/usr/bin/env python3
from __future__ import annotations

import os
import psycopg2
import psycopg2.extras

SQL_TABLES = """
select
    schemaname,
    tablename
from pg_tables
where schemaname not in ('pg_catalog','information_schema')
order by schemaname, tablename;
"""

SQL_SIZE = """
select
    relname as table_name,
    pg_total_relation_size(relid) as total_bytes
from pg_catalog.pg_statio_user_tables
order by pg_total_relation_size(relid) desc
limit 30;
"""

def classify(name: str) -> str:
    n = name.lower()

    if n.startswith("tmp_") or "temp" in n or "backup" in n or ".bak" in n:
        return "TEMP_OR_BACKUP"

    if any(x in n for x in [
        "audit", "scorecard", "quality", "gate", "quarantine",
        "rebuild", "shadow", "research", "walkforward",
        "attribution", "statistics", "provenance"
    ]):
        return "RESEARCH_CONTROL_LAYER"

    if any(x in n for x in [
        "trades", "fills", "orders", "positions",
        "portfolio", "runtime", "universe"
    ]):
        return "CORE_TRADING_LAYER"

    if any(x in n for x in [
        "bars", "candles", "market", "features", "signals"
    ]):
        return "MARKET_DATA_LAYER"

    return "UNCLASSIFIED"

def main() -> int:
    print("=== DATABASE ARCHITECTURE AUDIT V1 ===")
    print("mode=architecture_audit")
    print("runtime_allow=0")
    print("execution_enabled=0")

    with psycopg2.connect(os.environ["DATABASE_URL"]) as conn:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute(SQL_TABLES)
            tables = cur.fetchall()

            cur.execute(SQL_SIZE)
            sizes = cur.fetchall()

    buckets: dict[str, list[str]] = {}

    for r in tables:
        name = r["tablename"]
        bucket = classify(name)
        buckets.setdefault(bucket, []).append(name)

    print(f"DB_TABLE_TOTAL total={len(tables)}")

    for bucket, names in sorted(buckets.items()):
        print(f"DB_TABLE_BUCKET bucket={bucket} count={len(names)}")

    for bucket, names in sorted(buckets.items()):
        sample = ",".join(names[:20])
        print(f"DB_TABLE_SAMPLE bucket={bucket} sample={sample}")

    print("DB_TOP_SIZE_TABLES")
    for r in sizes:
        print(
            "DB_SIZE_ROW "
            f"table={r['table_name']} "
            f"bytes={r['total_bytes']}"
        )

    unclassified = len(buckets.get("UNCLASSIFIED", []))
    temp = len(buckets.get("TEMP_OR_BACKUP", []))

    if len(tables) > 300:
        status = "ARCHITECTURE_REVIEW_REQUIRED"
        reason = "too_many_tables"
    elif unclassified > 0 or temp > 0:
        status = "ARCHITECTURE_REVIEW_REQUIRED"
        reason = "unclassified_or_temp_tables"
    else:
        status = "ARCHITECTURE_OK"
        reason = "table_count_and_classification_ok"

    print(
        "DATABASE_ARCHITECTURE_VERDICT "
        f"status={status} "
        f"reason={reason} "
        f"total_tables={len(tables)} "
        f"unclassified={unclassified} "
        f"temp_or_backup={temp} "
        "runtime_allow=0 execution_enabled=0"
    )

    print("DATABASE_ARCHITECTURE_AUDIT_V1_OK")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
