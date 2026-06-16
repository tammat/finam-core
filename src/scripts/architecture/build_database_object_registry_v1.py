#!/usr/bin/env python3
from __future__ import annotations

import os
import psycopg2
import psycopg2.extras

DDL = """
create table if not exists database_object_registry_v1 (
    id bigserial primary key,
    created_at timestamptz not null default now(),

    schema_name text not null,
    object_name text not null,
    object_type text not null,

    object_category text not null,
    lifecycle_status text not null,
    classification_reason text not null,

    total_bytes bigint not null default 0,
    row_estimate bigint not null default 0,

    risk_level text not null,
    review_required boolean not null default true,

    runtime_allowed boolean not null default false,
    execution_enabled boolean not null default false,

    unique(schema_name, object_name, object_type)
);
"""

TRUNCATE = "truncate table database_object_registry_v1;"

OBJECTS_SQL = """
with rels as (
    select
        n.nspname as schema_name,
        c.relname as object_name,
        case c.relkind
            when 'r' then 'table'
            when 'p' then 'partitioned_table'
            when 'v' then 'view'
            when 'm' then 'materialized_view'
            when 'S' then 'sequence'
            when 'i' then 'index'
            else c.relkind::text
        end as object_type,
        coalesce(pg_total_relation_size(c.oid),0) as total_bytes,
        coalesce(c.reltuples::bigint,0) as row_estimate
    from pg_class c
    join pg_namespace n on n.oid=c.relnamespace
    where n.nspname not in ('pg_catalog','information_schema')
      and c.relkind in ('r','p','v','m','S')
)
select *
from rels
order by schema_name, object_type, object_name;
"""

INSERT = """
insert into database_object_registry_v1 (
    schema_name,
    object_name,
    object_type,
    object_category,
    lifecycle_status,
    classification_reason,
    total_bytes,
    row_estimate,
    risk_level,
    review_required,
    runtime_allowed,
    execution_enabled
)
values (
    %(schema_name)s,
    %(object_name)s,
    %(object_type)s,
    %(object_category)s,
    %(lifecycle_status)s,
    %(classification_reason)s,
    %(total_bytes)s,
    %(row_estimate)s,
    %(risk_level)s,
    %(review_required)s,
    false,
    false
)
on conflict(schema_name, object_name, object_type)
do update set
    created_at=now(),
    object_category=excluded.object_category,
    lifecycle_status=excluded.lifecycle_status,
    classification_reason=excluded.classification_reason,
    total_bytes=excluded.total_bytes,
    row_estimate=excluded.row_estimate,
    risk_level=excluded.risk_level,
    review_required=excluded.review_required,
    runtime_allowed=false,
    execution_enabled=false;
"""

SUMMARY = """
select
    object_category,
    lifecycle_status,
    risk_level,
    count(*) as objects
from database_object_registry_v1
group by object_category,lifecycle_status,risk_level
order by object_category,lifecycle_status,risk_level;
"""

TOTAL = """
select
    count(*) total,
    count(*) filter (where review_required=true) review_required,
    count(*) filter (where object_category='UNKNOWN_REVIEW') unknown_review,
    count(*) filter (where lifecycle_status='ARCHIVE_CANDIDATE') archive_candidates,
    count(*) filter (where lifecycle_status='DROP_CANDIDATE') drop_candidates
from database_object_registry_v1;
"""

TOP_UNKNOWN = """
select
    object_name,
    object_type,
    total_bytes,
    row_estimate,
    classification_reason
from database_object_registry_v1
where object_category='UNKNOWN_REVIEW'
order by total_bytes desc
limit 30;
"""

def classify(name: str, object_type: str, total_bytes: int) -> tuple[str, str, str, str, bool]:
    n = name.lower()

    if any(x in n for x in ["tmp", "temp", "backup", "_bak", "bak_"]):
        return (
            "ARCHIVE_CANDIDATE",
            "ARCHIVE_CANDIDATE",
            "temporary_or_backup_like_name",
            "MEDIUM",
            True,
        )

    if n in {
        "trades",
        "fills",
        "orders",
        "positions",
        "managed_positions",
        "closed_trades",
        "broker_order_snapshots",
        "broker_reconciliation_events",
        "portfolio_snapshots",
        "portfolio_pnl_events",
        "portfolio_governance_events",
    }:
        return (
            "CORE_KEEP",
            "ACTIVE_KEEP",
            "core_trading_accounting",
            "HIGH",
            False,
        )

    if any(x in n for x in ["market_ticks", "market_bars", "market_data", "candles", "bars"]):
        risk = "HIGH" if total_bytes > 1_000_000_000 else "MEDIUM"
        return (
            "MARKET_DATA_KEEP",
            "ACTIVE_KEEP",
            "market_data_storage",
            risk,
            total_bytes > 1_000_000_000,
        )

    if any(x in n for x in ["runtime", "universe", "allocator", "rotation"]):
        return (
            "RUNTIME_KEEP",
            "ACTIVE_REVIEW",
            "runtime_control_or_telemetry",
            "MEDIUM",
            True,
        )

    if any(x in n for x in [
        "research", "walkforward", "scorecard", "audit", "quality", "gate",
        "quarantine", "rebuild", "attribution", "statistics", "provenance",
        "shadow", "v1", "v2", "v3"
    ]):
        return (
            "RESEARCH_KEEP",
            "RESEARCH_REVIEW",
            "research_or_experimental_layer",
            "LOW",
            True,
        )

    return (
        "UNKNOWN_REVIEW",
        "MANUAL_REVIEW",
        "needs_manual_classification",
        "MEDIUM",
        True,
    )

def main() -> int:
    print("=== DATABASE OBJECT REGISTRY V1 ===")
    print("mode=architecture_registry")
    print("runtime_allow=0")
    print("execution_enabled=0")

    with psycopg2.connect(os.environ["DATABASE_URL"]) as conn:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute(DDL)
            cur.execute(TRUNCATE)
            cur.execute(OBJECTS_SQL)
            objects = cur.fetchall()

            for obj in objects:
                category, lifecycle, reason, risk, review = classify(
                    obj["object_name"],
                    obj["object_type"],
                    int(obj["total_bytes"] or 0),
                )
                payload = {
                    "schema_name": obj["schema_name"],
                    "object_name": obj["object_name"],
                    "object_type": obj["object_type"],
                    "object_category": category,
                    "lifecycle_status": lifecycle,
                    "classification_reason": reason,
                    "total_bytes": int(obj["total_bytes"] or 0),
                    "row_estimate": int(obj["row_estimate"] or 0),
                    "risk_level": risk,
                    "review_required": review,
                }
                cur.execute(INSERT, payload)

            cur.execute(TOTAL)
            total = cur.fetchone()

            cur.execute(SUMMARY)
            summary = cur.fetchall()

            cur.execute(TOP_UNKNOWN)
            unknown = cur.fetchall()

        conn.commit()

    print(
        "DB_OBJECT_REGISTRY_TOTAL "
        f"total={total['total']} "
        f"review_required={total['review_required']} "
        f"unknown_review={total['unknown_review']} "
        f"archive_candidates={total['archive_candidates']} "
        f"drop_candidates={total['drop_candidates']} "
        "runtime_allow=0 execution_enabled=0"
    )

    for r in summary:
        print(
            "DB_OBJECT_REGISTRY_BUCKET "
            f"category={r['object_category']} "
            f"lifecycle={r['lifecycle_status']} "
            f"risk={r['risk_level']} "
            f"objects={r['objects']}"
        )

    for r in unknown:
        print(
            "DB_OBJECT_UNKNOWN_ROW "
            f"object={r['object_name']} "
            f"type={r['object_type']} "
            f"bytes={r['total_bytes']} "
            f"rows_est={r['row_estimate']} "
            f"reason={r['classification_reason']}"
        )

    if int(total["unknown_review"] or 0) > 0:
        status = "REGISTRY_CREATED_REVIEW_REQUIRED"
        reason = "unknown_objects_exist"
    else:
        status = "REGISTRY_CREATED_NO_UNKNOWN"
        reason = "all_objects_classified"

    print(
        "DB_OBJECT_REGISTRY_VERDICT "
        f"status={status} "
        f"reason={reason} "
        f"unknown_review={total['unknown_review']} "
        "runtime_allow=0 execution_enabled=0"
    )

    print("DATABASE_OBJECT_REGISTRY_V1_OK")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
