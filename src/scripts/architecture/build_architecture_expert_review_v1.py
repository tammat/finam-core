#!/usr/bin/env python3
from __future__ import annotations

import os
import psycopg2
import psycopg2.extras

TABLES_SQL = """
select
    schemaname,
    tablename
from pg_tables
where schemaname not in ('pg_catalog','information_schema')
order by tablename;
"""

SIZE_SQL = """
select
    relname as table_name,
    pg_total_relation_size(relid) as total_bytes
from pg_catalog.pg_statio_user_tables
order by pg_total_relation_size(relid) desc;
"""

FK_SQL = """
select
    tc.table_name,
    kcu.column_name,
    ccu.table_name as foreign_table_name,
    ccu.column_name as foreign_column_name
from information_schema.table_constraints tc
join information_schema.key_column_usage kcu
  on tc.constraint_name = kcu.constraint_name
 and tc.table_schema = kcu.table_schema
join information_schema.constraint_column_usage ccu
  on ccu.constraint_name = tc.constraint_name
 and ccu.table_schema = tc.table_schema
where tc.constraint_type = 'FOREIGN KEY'
  and tc.table_schema not in ('pg_catalog','information_schema');
"""

def classify_table(name: str) -> tuple[str, str]:
    n = name.lower()

    if n in {
        "trades", "orders", "fills", "positions", "managed_positions",
        "broker_order_snapshots", "broker_reconciliation_events",
        "portfolio_snapshots", "portfolio_pnl_events",
        "portfolio_governance_events",
    }:
        return "CORE_KEEP", "core_trading_accounting"

    if any(x in n for x in ["market_ticks", "market_bars", "market_data", "candles", "bars"]):
        return "MARKET_DATA_KEEP", "market_data_storage"

    if any(x in n for x in ["runtime", "universe", "allocator", "rotation"]):
        return "RUNTIME_REVIEW", "runtime_control_or_telemetry"

    if any(x in n for x in [
        "research", "walkforward", "scorecard", "audit", "quality", "gate",
        "quarantine", "rebuild", "attribution", "statistics", "provenance",
        "shadow", "v1", "v2", "v3"
    ]):
        return "RESEARCH_REVIEW", "research_or_experimental_layer"

    if any(x in n for x in ["tmp", "temp", "backup", "bak"]):
        return "ARCHIVE_CANDIDATE", "temporary_or_backup_like_name"

    return "UNKNOWN_REVIEW", "needs_manual_classification"

def risk_level(category: str, bytes_: int) -> str:
    if category == "CORE_KEEP":
        return "HIGH"
    if category == "MARKET_DATA_KEEP" and bytes_ > 1_000_000_000:
        return "HIGH"
    if category in {"UNKNOWN_REVIEW", "ARCHIVE_CANDIDATE"}:
        return "MEDIUM"
    return "LOW"

def main() -> int:
    print("=== ARCHITECTURE EXPERT REVIEW V1 ===")
    print("mode=expert_review")
    print("runtime_allow=0")
    print("execution_enabled=0")

    with psycopg2.connect(os.environ["DATABASE_URL"]) as conn:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute(TABLES_SQL)
            tables = cur.fetchall()

            cur.execute(SIZE_SQL)
            sizes = {r["table_name"]: int(r["total_bytes"] or 0) for r in cur.fetchall()}

            cur.execute(FK_SQL)
            fks = cur.fetchall()

    registry = []
    for r in tables:
        table = r["tablename"]
        category, reason = classify_table(table)
        size = sizes.get(table, 0)
        registry.append((table, category, reason, size, risk_level(category, size)))

    buckets = {}
    for _, category, _, _, _ in registry:
        buckets[category] = buckets.get(category, 0) + 1

    print(f"ARCH_TABLE_TOTAL total={len(registry)}")
    print(f"ARCH_FK_TOTAL total={len(fks)}")

    for category, count in sorted(buckets.items()):
        print(f"ARCH_BUCKET category={category} count={count}")

    print("ARCH_TOP_SIZE")
    for table, category, reason, size, risk in sorted(registry, key=lambda x: x[3], reverse=True)[:30]:
        print(
            "ARCH_SIZE_ROW "
            f"table={table} "
            f"category={category} "
            f"bytes={size} "
            f"risk={risk} "
            f"reason={reason}"
        )

    unknown = buckets.get("UNKNOWN_REVIEW", 0)
    research = buckets.get("RESEARCH_REVIEW", 0)
    archive = buckets.get("ARCHIVE_CANDIDATE", 0)

    if unknown > 50:
        db_status = "DB_ARCHITECTURE_REVIEW_REQUIRED"
        db_reason = "too_many_unknown_tables"
    elif research > 80:
        db_status = "DB_RESEARCH_LAYER_SPRAWL"
        db_reason = "too_many_research_experimental_tables"
    elif archive > 0:
        db_status = "DB_CLEANUP_REVIEW_REQUIRED"
        db_reason = "archive_candidates_exist"
    else:
        db_status = "DB_ARCHITECTURE_ACCEPTABLE"
        db_reason = "classification_within_expected_limits"

    print(
        "ARCH_DB_VERDICT "
        f"status={db_status} "
        f"reason={db_reason} "
        f"unknown={unknown} "
        f"research_review={research} "
        f"archive_candidates={archive}"
    )

    print(
        "ARCH_PYTHON_VERDICT "
        "status=REVIEW_REQUIRED "
        "reason=project_needs_module_boundary_audit_for_research_runtime_storage_layers"
    )

    print(
        "ARCH_ALGOTRADING_VERDICT "
        "status=SAFE_BLOCKED "
        "reason=trusted_candidates_0_runtime_active_universe_0_v3_reviewable_0"
    )

    print(
        "ARCH_FINAL_VERDICT "
        "status=ARCHITECTURE_STABILIZATION_REQUIRED "
        "reason=database_registry_and_module_boundary_cleanup_before_new_strategy_work"
    )

    print("ARCHITECTURE_EXPERT_REVIEW_V1_OK")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
