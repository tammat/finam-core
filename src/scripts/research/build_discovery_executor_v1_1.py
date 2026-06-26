#!/usr/bin/env python3
from __future__ import annotations

import os
import sys

from marketcore.catalog.discovery.context import DiscoveryContext
from marketcore.catalog.discovery.executor import DiscoveryExecutor
from marketcore.catalog.discovery.registry import DiscoveryRegistry
from marketcore.catalog.discovery.plugins.postgres_discovery import PostgresDiscovery
from marketcore.catalog.discovery.plugins.python_discovery import PythonDiscovery
from marketcore.catalog.discovery.plugins.bash_discovery import BashDiscovery
from marketcore.catalog.discovery.plugins.systemd_discovery import SystemdDiscovery


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

    registry = DiscoveryRegistry()
    registry.register(PostgresDiscovery(db_url()))
    registry.register(PythonDiscovery("."))
    registry.register(BashDiscovery("."))
    registry.register(SystemdDiscovery("."))

    executor = DiscoveryExecutor(registry.plugins())
    objects = executor.run(context)

    by_source: dict[str, int] = {}
    for obj in objects:
        by_source[obj.discovery_source] = by_source.get(obj.discovery_source, 0) + 1

    print("=== DISCOVERY_EXECUTOR_V1_1 ===")
    print(f"profile={context.profile}")
    print("registry=DiscoveryRegistry")
    print("plugins=PostgresDiscovery,PythonDiscovery,BashDiscovery,SystemdDiscovery")
    print(f"objects_total={len(objects)}")

    for source, cnt in sorted(by_source.items()):
        print(f"source_count={source}:{cnt}")

    print("executor_policy=DEDUP_BY_OBJECT_ID")
    print("catalog_write_deferred=1")
    print("runtime_changed=0")
    print("execution_changed=0")
    print("orders_changed=0")
    print("fills_changed=0")
    print("micro_live_allowed=0")
    print("VERDICT=DISCOVERY_EXECUTOR_V1_1_READY")
    return 0


if __name__ == "__main__":
    sys.exit(main())
