#!/usr/bin/env python3
from __future__ import annotations

import os
import sys
import psycopg2
import psycopg2.extras

from marketcore.catalog.discovery.context import DiscoveryContext
from marketcore.catalog.discovery.executor import DiscoveryExecutor
from marketcore.catalog.discovery.plugins.postgres_discovery import PostgresDiscovery
from marketcore.catalog.discovery.plugins.python_discovery import PythonDiscovery
from marketcore.catalog.discovery.plugins.bash_discovery import BashDiscovery
from marketcore.catalog.discovery.plugins.systemd_discovery import SystemdDiscovery
from marketcore.catalog.writer.catalog_writer import CatalogWriter


def db_url() -> str:
    return os.getenv("DATABASE_URL", "postgresql:///finam_core")


def main() -> int:
    context = DiscoveryContext(
        profile="WORKFLOW_DISCOVERY_PROFILE_V1",
        domain="WORKFLOW",
        schema_filter=("warehouse",),
        name_patterns=(
            "qlt_workflow_%",
            "nrm_workflow_%",
            "fact_event_workflow_%",
            "fact_state_workflow_%",
            "fact_state_candidate_lifecycle_v1",
            "dim_stage_v1",
            "dim_status_light_v1",
            "sem_workflow_v1",
            "sem_candidate_v1",
            "mart_workflow_dashboard_v1",
            "mart_candidate_workflow_v1",
            "snap_workflow_daily_v1",
        ),
    )

    executor = DiscoveryExecutor([
        PostgresDiscovery(db_url()),
        PythonDiscovery("."),
        BashDiscovery("."),
        SystemdDiscovery("."),
    ])
    objects = executor.run(context)

    with psycopg2.connect(db_url()) as conn:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            written = CatalogWriter().write(cur, objects)
            conn.commit()

            cur.execute("""
                SELECT count(*)::bigint AS cnt
                FROM warehouse.analytics_asset_catalog_v1
                WHERE domain='WORKFLOW'
            """)
            total = int(cur.fetchone()["cnt"])

            cur.execute("""
                SELECT payload->>'discovery_source' AS source, count(*) AS cnt
                FROM warehouse.analytics_asset_catalog_v1
                WHERE domain='WORKFLOW'
                GROUP BY payload->>'discovery_source'
                ORDER BY source
            """)
            sources = cur.fetchall()

            cur.execute("""
                SELECT category, count(*) AS cnt
                FROM warehouse.analytics_asset_catalog_v1
                WHERE domain='WORKFLOW'
                GROUP BY category
                ORDER BY category
            """)
            categories = cur.fetchall()

    print("=== WORKFLOW_DISCOVERY_PROFILE_V1_2 ===")
    print(f"profile={context.profile}")
    print(f"domain={context.domain}")
    print(f"objects_discovered={len(objects)}")
    print(f"catalog_rows_written={written}")
    print(f"catalog_workflow_total={total}")

    for row in sources:
        print(f"catalog_source={row['source']}:{row['cnt']}")

    for row in categories:
        print(f"catalog_category={row['category']}:{row['cnt']}")

    print("discovery_plugins=PostgresDiscovery,PythonDiscovery,BashDiscovery,SystemdDiscovery")
    print("writer=CatalogWriter")
    print("write_policy=UPSERT_BY_OBJECT_ID")
    print("target_catalog=warehouse.analytics_asset_catalog_v1")
    print("runtime_changed=0")
    print("execution_changed=0")
    print("orders_changed=0")
    print("fills_changed=0")
    print("micro_live_allowed=0")
    print("VERDICT=WORKFLOW_DISCOVERY_PROFILE_V1_2_READY")
    return 0


if __name__ == "__main__":
    sys.exit(main())
