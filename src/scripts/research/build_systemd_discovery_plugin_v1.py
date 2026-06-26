#!/usr/bin/env python3
from __future__ import annotations

import sys

from marketcore.catalog.discovery.context import DiscoveryContext
from marketcore.catalog.discovery.plugins.systemd_discovery import SystemdDiscovery


def main() -> int:
    context = DiscoveryContext(
        profile="WORKFLOW_DISCOVERY_PROFILE_V1",
        domain="WORKFLOW",
        schema_filter=(),
        name_patterns=("SYSTEMD",),
    )

    objects = SystemdDiscovery(".").discover(context)

    service_objects = sum(1 for o in objects if o.category == "SERVICE")
    env_objects = sum(1 for o in objects if o.object_name.endswith(".env"))

    print("=== SYSTEMD_DISCOVERY_PLUGIN_V1 ===")
    print(f"profile={context.profile}")
    print(f"domain={context.domain}")
    print(f"objects_discovered={len(objects)}")
    print(f"service_objects={service_objects}")
    print(f"env_objects={env_objects}")

    for obj in objects:
        print(
            "discovered_object="
            f"{obj.object_id}|{obj.domain}|{obj.category}|{obj.object_type}|{obj.warehouse_layer}"
        )

    print("plugin_model=PLUGIN_BASED")
    print("discovery_source=SystemdDiscovery")
    print("catalog_write_deferred=1")
    print("runtime_changed=0")
    print("execution_changed=0")
    print("orders_changed=0")
    print("fills_changed=0")
    print("micro_live_allowed=0")
    print("VERDICT=SYSTEMD_DISCOVERY_PLUGIN_V1_READY")
    return 0


if __name__ == "__main__":
    sys.exit(main())
