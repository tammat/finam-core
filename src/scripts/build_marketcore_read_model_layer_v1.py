from __future__ import annotations

import os
import uuid
from datetime import datetime, timezone
from decimal import Decimal

import psycopg2

DB = os.getenv("DATABASE_URL", "postgresql:///finam_core")
SOURCE_VERSION = "MARKETCORE_READ_MODEL_LAYER_V1"


def table_exists(cur, table: str) -> bool:
    cur.execute("SELECT to_regclass(%s);", (table,))
    return cur.fetchone()[0] is not None


def count_rows(cur, table: str, where_sql: str = "TRUE") -> int:
    if not table_exists(cur, table):
        return 0
    cur.execute(f"SELECT count(*) FROM {table} WHERE {where_sql};")
    return int(cur.fetchone()[0] or 0)


def main() -> None:
    build_id = str(uuid.uuid4())
    now = datetime.now(timezone.utc)

    with psycopg2.connect(DB) as conn:
        with conn.cursor() as cur:
            planned = Decimal(os.getenv("MARKETCORE_PLANNED_CAPITAL_RUB", "500000"))

            cur.execute("""
                INSERT INTO marketcore_ui.capital_summary_v1 (
                    id, planned_capital, working_capital, available_capital,
                    today_pnl, refreshed_at, source_version, build_id
                )
                VALUES (1, %s, 0, %s, 0, %s, %s, %s)
                ON CONFLICT (id) DO UPDATE SET
                    planned_capital = EXCLUDED.planned_capital,
                    working_capital = EXCLUDED.working_capital,
                    available_capital = EXCLUDED.available_capital,
                    today_pnl = EXCLUDED.today_pnl,
                    refreshed_at = EXCLUDED.refreshed_at,
                    source_version = EXCLUDED.source_version,
                    build_id = EXCLUDED.build_id;
            """, (planned, planned, now, SOURCE_VERSION, build_id))

            research_candidates = count_rows(
                cur,
                "analytics_global_edge_expanded_runtime_candidates_v2",
                "candidate_status='RESEARCH_CANDIDATE'",
            )

            paper_edges = count_rows(
                cur,
                "analytics_global_edge_top3_runtime_approval_board_v1",
                "board_decision='APPROVE_PAPER'",
            )

            shadow_edges = count_rows(
                cur,
                "analytics_global_edge_top3_shadow_runtime_execution_v1",
                "shadow_status='SHADOW_ACTIVE'",
            )

            oos_pass = count_rows(
                cur,
                "analytics_global_edge_top3_oos_validation_v1",
                "oos_status='OOS_PASS'",
            )

            cur.execute("""
                INSERT INTO marketcore_ui.profit_summary_v1 (
                    id, production_edges, paper_edges, shadow_edges,
                    research_candidates, refreshed_at, source_version, build_id
                )
                VALUES (1, 0, %s, %s, %s, %s, %s, %s)
                ON CONFLICT (id) DO UPDATE SET
                    production_edges = EXCLUDED.production_edges,
                    paper_edges = EXCLUDED.paper_edges,
                    shadow_edges = EXCLUDED.shadow_edges,
                    research_candidates = EXCLUDED.research_candidates,
                    refreshed_at = EXCLUDED.refreshed_at,
                    source_version = EXCLUDED.source_version,
                    build_id = EXCLUDED.build_id;
            """, (paper_edges, shadow_edges, research_candidates, now, SOURCE_VERSION, build_id))

            cur.execute("""
                INSERT INTO marketcore_ui.research_summary_v1 (
                    id, pipeline_status, top3_status, research_candidates,
                    oos_pass, paper_ready, refreshed_at, source_version, build_id
                )
                VALUES (1, %s, %s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT (id) DO UPDATE SET
                    pipeline_status = EXCLUDED.pipeline_status,
                    top3_status = EXCLUDED.top3_status,
                    research_candidates = EXCLUDED.research_candidates,
                    oos_pass = EXCLUDED.oos_pass,
                    paper_ready = EXCLUDED.paper_ready,
                    refreshed_at = EXCLUDED.refreshed_at,
                    source_version = EXCLUDED.source_version,
                    build_id = EXCLUDED.build_id;
            """, (
                "COMPLETE",
                "COMPLETE" if paper_edges >= 3 else "IN_PROGRESS",
                research_candidates,
                oos_pass,
                paper_edges,
                now,
                SOURCE_VERSION,
                build_id,
            ))

            runtime_allowed_count = 0
            for table in (
                "analytics_global_edge_expanded_runtime_candidates_v2",
                "analytics_global_edge_runtime_candidates_v2",
            ):
                if table_exists(cur, table):
                    runtime_allowed_count += count_rows(
                        cur,
                        table,
                        "COALESCE(runtime_allowed,false)=true "
                        "OR COALESCE(execution_allowed,false)=true "
                        "OR COALESCE(micro_live_allowed,false)=true",
                    )

            cur.execute("""
                INSERT INTO marketcore_ui.risk_summary_v1 (
                    id, runtime_allowed, execution_allowed, micro_live_allowed,
                    daily_risk_pct, refreshed_at, source_version, build_id
                )
                VALUES (1, %s, false, false, 0, %s, %s, %s)
                ON CONFLICT (id) DO UPDATE SET
                    runtime_allowed = EXCLUDED.runtime_allowed,
                    execution_allowed = EXCLUDED.execution_allowed,
                    micro_live_allowed = EXCLUDED.micro_live_allowed,
                    daily_risk_pct = EXCLUDED.daily_risk_pct,
                    refreshed_at = EXCLUDED.refreshed_at,
                    source_version = EXCLUDED.source_version,
                    build_id = EXCLUDED.build_id;
            """, (runtime_allowed_count > 0, now, SOURCE_VERSION, build_id))

            cur.execute("""
                INSERT INTO marketcore_ui.program_summary_v1 (
                    id, quarter, platform_status, research_status, top3_status,
                    paper_status, marketcore_status, refreshed_at, source_version, build_id
                )
                VALUES (1, 'Q3 2026', 'COMPLETE', 'COMPLETE', 'COMPLETE',
                        %s, 'IN_PROGRESS', %s, %s, %s)
                ON CONFLICT (id) DO UPDATE SET
                    quarter = EXCLUDED.quarter,
                    platform_status = EXCLUDED.platform_status,
                    research_status = EXCLUDED.research_status,
                    top3_status = EXCLUDED.top3_status,
                    paper_status = EXCLUDED.paper_status,
                    marketcore_status = EXCLUDED.marketcore_status,
                    refreshed_at = EXCLUDED.refreshed_at,
                    source_version = EXCLUDED.source_version,
                    build_id = EXCLUDED.build_id;
            """, ("READY" if paper_edges > 0 else "WAITING", now, SOURCE_VERSION, build_id))

    print("=== MARKETCORE_READ_MODEL_BUILDER_V1 ===")
    print(f"build_id={build_id}")
    print(f"research_candidates={research_candidates}")
    print(f"paper_edges={paper_edges}")
    print(f"shadow_edges={shadow_edges}")
    print(f"oos_pass={oos_pass}")
    print("runtime_changed=0")
    print("execution_changed=0")
    print("orders_changed=0")
    print("fills_changed=0")
    print("micro_live_allowed=0")
    print("VERDICT=MARKETCORE_READ_MODEL_BUILDER_V1_READY")


if __name__ == "__main__":
    main()
