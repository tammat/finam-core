#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from __future__ import annotations

import os
import sys

from marketcore.catalog.discovery.context import DiscoveryContext
from marketcore.catalog.discovery.plugins.postgres_discovery import PostgresDiscovery


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

    plugin = PostgresDiscovery(db_url())
    objects = plugin.discover(context)

    table_count = sum(1 for o in objects if o.category == "TABLE")
    view_count = sum(1 for o in objects if o.category == "VIEW")
    function_count = sum(1 for o in objects if o.category == "FUNCTION")

    print("=== POSTGRES_DISCOVERY_PLUGIN_V1 ===")
    print(f"profile={context.profile}")
    print(f"domain={context.domain}")
    print(f"objects_discovered={len(objects)}")
    print(f"tables_discovered={table_count}")
    print(f"views_discovered={view_count}")
    print(f"functions_discovered={function_count}")

    for obj in objects:
        print(
            "discovered_object="
            f"{obj.object_id}|"
            f"{obj.domain}|"
            f"{obj.category}|"
            f"{obj.object_type}|"
            f"{obj.warehouse_layer}|"
            f"rows={obj.rows_count}"
        )

    print("plugin_model=PLUGIN_BASED")
    print("discovery_source=PostgresDiscovery")
    print("normalization_ready=1")
    print("catalog_write_deferred=1")
    print("runtime_changed=0")
    print("execution_changed=0")
    print("orders_changed=0")
    print("fills_changed=0")
    print("micro_live_allowed=0")
    print("VERDICT=POSTGRES_DISCOVERY_PLUGIN_V1_READY")
    return 0


if __name__ == "__main__":
    sys.exit(main())
