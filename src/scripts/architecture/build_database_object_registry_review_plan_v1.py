#!/usr/bin/env python3
from __future__ import annotations

import os
import psycopg2
import psycopg2.extras

DDL = """
create table if not exists database_object_registry_review_plan_v1 (
    id bigserial primary key,
    created_at timestamptz not null default now(),

    schema_name text not null,
    object_name text not null,
    object_type text not null,

    current_category text not null,
    current_lifecycle_status text not null,

    proposed_action text not null,
    proposed_category text not null,
    proposed_lifecycle_status text not null,
    action_reason text not null,

    total_bytes bigint not null default 0,
    row_estimate bigint not null default 0,

    risk_level text not null,
    requires_manual_approval boolean not null default true,

    runtime_allowed boolean not null default false,
    execution_enabled boolean not null default false,

    unique(schema_name, object_name, object_type)
);
"""

TRUNCATE = "truncate table database_object_registry_review_plan_v1;"

SOURCE_SQL = """
select
    schema_name,
    object_name,
    object_type,
    object_category,
    lifecycle_status,
    total_bytes,
    row_estimate,
    risk_level
from database_object_registry_v1
where object_category='UNKNOWN_REVIEW'
   or lifecycle_status in ('MANUAL_REVIEW','ARCHIVE_CANDIDATE')
order by total_bytes desc, object_name;
"""

INSERT = """
insert into database_object_registry_review_plan_v1 (
    schema_name,
    object_name,
    object_type,
    current_category,
    current_lifecycle_status,
    proposed_action,
    proposed_category,
    proposed_lifecycle_status,
    action_reason,
    total_bytes,
    row_estimate,
    risk_level,
    requires_manual_approval,
    runtime_allowed,
    execution_enabled
)
values (
    %(schema_name)s,
    %(object_name)s,
    %(object_type)s,
    %(current_category)s,
    %(current_lifecycle_status)s,
    %(proposed_action)s,
    %(proposed_category)s,
    %(proposed_lifecycle_status)s,
    %(action_reason)s,
    %(total_bytes)s,
    %(row_estimate)s,
    %(risk_level)s,
    %(requires_manual_approval)s,
    false,
    false
)
on conflict(schema_name, object_name, object_type)
do update set
    created_at=now(),
    current_category=excluded.current_category,
    current_lifecycle_status=excluded.current_lifecycle_status,
    proposed_action=excluded.proposed_action,
    proposed_category=excluded.proposed_category,
    proposed_lifecycle_status=excluded.proposed_lifecycle_status,
    action_reason=excluded.action_reason,
    total_bytes=excluded.total_bytes,
    row_estimate=excluded.row_estimate,
    risk_level=excluded.risk_level,
    requires_manual_approval=excluded.requires_manual_approval,
    runtime_allowed=false,
    execution_enabled=false;
"""

SUMMARY = """
select
    proposed_action,
    proposed_category,
    proposed_lifecycle_status,
    risk_level,
    count(*) objects
from database_object_registry_review_plan_v1
group by proposed_action, proposed_category, proposed_lifecycle_status, risk_level
order by proposed_action, proposed_category, risk_level;
"""

TOTAL = """
select
    count(*) total,
    count(*) filter (where requires_manual_approval=true) manual_approval,
    count(*) filter (where proposed_action='DROP_CANDIDATE') drop_candidates,
    count(*) filter (where proposed_action='ARCHIVE_CANDIDATE') archive_candidates,
    count(*) filter (where proposed_action='RECLASSIFY_CORE') core_reclassify,
    count(*) filter (where proposed_action='RECLASSIFY_RUNTIME') runtime_reclassify,
    count(*) filter (where proposed_action='RECLASSIFY_RESEARCH') research_reclassify,
    count(*) filter (where proposed_action='RECLASSIFY_MARKET_DATA') market_reclassify
from database_object_registry_review_plan_v1;
"""

TOP_ROWS = """
select
    object_name,
    object_type,
    proposed_action,
    proposed_category,
    proposed_lifecycle_status,
    total_bytes,
    row_estimate,
    risk_level,
    action_reason
from database_object_registry_review_plan_v1
order by total_bytes desc
limit 40;
"""

def propose(name: str, object_type: str, total_bytes: int) -> tuple[str, str, str, str, str, bool]:
    n = name.lower()

    if any(x in n for x in ["tmp", "temp", "backup", "_bak", "bak_"]):
        return (
            "ARCHIVE_CANDIDATE",
            "ARCHIVE_CANDIDATE",
            "ARCHIVE_REVIEW",
            "temporary_or_backup_like_name",
            "MEDIUM",
            True,
        )

    if any(x in n for x in [
        "broker", "oms", "order", "orders", "fill", "fills", "trade_context",
        "trade_risk", "risk_events", "position", "positions", "portfolio",
        "execution", "reconciliation"
    ]):
        return (
            "RECLASSIFY_CORE",
            "CORE_KEEP",
            "ACTIVE_REVIEW",
            "core_trading_execution_or_risk_context",
            "HIGH",
            True,
        )

    if any(x in n for x in [
        "signal", "feature", "regime", "radar", "opportunity",
        "instrument", "liquidity", "flow", "event_calendar"
    ]):
        return (
            "RECLASSIFY_MARKET_DATA",
            "MARKET_DATA_KEEP",
            "ACTIVE_REVIEW",
            "market_data_signal_feature_or_reference",
            "MEDIUM",
            True,
        )

    if any(x in n for x in [
        "profit_lock", "trailing", "take_profit", "stop", "exit_policy",
        "performance", "drawdown", "pnl", "outcome", "analytics"
    ]):
        return (
            "RECLASSIFY_RESEARCH",
            "RESEARCH_KEEP",
            "RESEARCH_REVIEW",
            "analytics_exit_or_performance_research",
            "LOW",
            True,
        )

    if any(x in n for x in [
        "runtime", "guard", "policy", "state", "supervisor", "allocator"
    ]):
        return (
            "RECLASSIFY_RUNTIME",
            "RUNTIME_KEEP",
            "ACTIVE_REVIEW",
            "runtime_control_policy_or_state",
            "MEDIUM",
            True,
        )

    return (
        "MANUAL_REVIEW",
        "UNKNOWN_REVIEW",
        "MANUAL_REVIEW",
        "no_safe_rule_matched",
        "MEDIUM",
        True,
    )

def main() -> int:
    print("=== DATABASE OBJECT REGISTRY REVIEW PLAN V1 ===")
    print("mode=architecture_review_plan")
    print("runtime_allow=0")
    print("execution_enabled=0")

    with psycopg2.connect(os.environ["DATABASE_URL"]) as conn:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute(DDL)
            cur.execute(TRUNCATE)
            cur.execute(SOURCE_SQL)
            rows = cur.fetchall()

            for r in rows:
                action, category, lifecycle, reason, risk, manual = propose(
                    r["object_name"],
                    r["object_type"],
                    int(r["total_bytes"] or 0),
                )

                payload = {
                    "schema_name": r["schema_name"],
                    "object_name": r["object_name"],
                    "object_type": r["object_type"],
                    "current_category": r["object_category"],
                    "current_lifecycle_status": r["lifecycle_status"],
                    "proposed_action": action,
                    "proposed_category": category,
                    "proposed_lifecycle_status": lifecycle,
                    "action_reason": reason,
                    "total_bytes": int(r["total_bytes"] or 0),
                    "row_estimate": int(r["row_estimate"] or 0),
                    "risk_level": risk,
                    "requires_manual_approval": manual,
                }
                cur.execute(INSERT, payload)

            cur.execute(TOTAL)
            total = cur.fetchone()

            cur.execute(SUMMARY)
            summary = cur.fetchall()

            cur.execute(TOP_ROWS)
            top_rows = cur.fetchall()

        conn.commit()

    print(
        "DB_REGISTRY_REVIEW_PLAN_TOTAL "
        f"total={total['total']} "
        f"manual_approval={total['manual_approval']} "
        f"drop_candidates={total['drop_candidates']} "
        f"archive_candidates={total['archive_candidates']} "
        f"core_reclassify={total['core_reclassify']} "
        f"runtime_reclassify={total['runtime_reclassify']} "
        f"research_reclassify={total['research_reclassify']} "
        f"market_reclassify={total['market_reclassify']} "
        "runtime_allow=0 execution_enabled=0"
    )

    for r in summary:
        print(
            "DB_REGISTRY_REVIEW_BUCKET "
            f"action={r['proposed_action']} "
            f"category={r['proposed_category']} "
            f"lifecycle={r['proposed_lifecycle_status']} "
            f"risk={r['risk_level']} "
            f"objects={r['objects']}"
        )

    for r in top_rows:
        print(
            "DB_REGISTRY_REVIEW_ROW "
            f"object={r['object_name']} "
            f"type={r['object_type']} "
            f"action={r['proposed_action']} "
            f"category={r['proposed_category']} "
            f"lifecycle={r['proposed_lifecycle_status']} "
            f"bytes={r['total_bytes']} "
            f"rows_est={r['row_estimate']} "
            f"risk={r['risk_level']} "
            f"reason={r['action_reason']}"
        )

    print(
        "DB_REGISTRY_REVIEW_PLAN_VERDICT "
        "status=PLAN_CREATED_NO_DELETE "
        "reason=all_actions_require_manual_approval "
        f"manual_approval={total['manual_approval']} "
        "runtime_allow=0 execution_enabled=0"
    )

    print("DATABASE_OBJECT_REGISTRY_REVIEW_PLAN_V1_OK")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
