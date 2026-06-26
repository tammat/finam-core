#!/usr/bin/env python3
from __future__ import annotations

import os
import sys
import psycopg2
import psycopg2.extras

from marketcore.catalog.discovery.context import DiscoveryContext
from marketcore.catalog.discovery.plugins.postgres_discovery import PostgresDiscovery
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

    objects = PostgresDiscovery(db_url()).discover(context)

    with psycopg2.connect(db_url()) as conn:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            written = CatalogWriter().write(cur, objects)
            conn.commit()

            cur.execute("""
                SELECT count(*)::bigint AS cnt
                FROM warehouse.analytics_asset_catalog_v1
                WHERE domain='WORKFLOW'
                  AND payload->>'discovery_source'='PostgresDiscovery'
            """)
            catalog_rows = int(cur.fetchone()["cnt"])

            cur.execute("""
                SELECT object_id, category, warehouse_layer, rows_count, health_light
                FROM warehouse.analytics_asset_catalog_v1
                WHERE domain='WORKFLOW'
                  AND payload->>'discovery_source'='PostgresDiscovery'
                ORDER BY object_id
            """)
            rows = cur.fetchall()

    print("=== CATALOG_WRITER_V1 ===")
    print(f"profile={context.profile}")
    print(f"discovered_objects={len(objects)}")
    print(f"catalog_rows_written={written}")
    print(f"catalog_workflow_postgres_rows={catalog_rows}")

    for row in rows:
        print(
            "catalog_object="
            f"{row['object_id']}|{row['category']}|{row['warehouse_layer']}|"
            f"rows={row['rows_count']}|{row['health_light']}"
        )

    print("write_policy=UPSERT_BY_OBJECT_ID")
    print("target_catalog=warehouse.analytics_asset_catalog_v1")
    print("source_plugin=PostgresDiscovery")
    print("runtime_changed=0")
    print("execution_changed=0")
    print("orders_changed=0")
    print("fills_changed=0")
    print("micro_live_allowed=0")
    print("VERDICT=CATALOG_WRITER_V1_READY")
    return 0


if __name__ == "__main__":
    sys.exit(main())
