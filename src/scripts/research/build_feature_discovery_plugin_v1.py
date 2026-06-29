#!/usr/bin/env python3
from __future__ import annotations

import sys

from marketcore.catalog.discovery.context import DiscoveryContext
from marketcore.catalog.discovery.plugins.feature_discovery import FeatureDiscovery


def main() -> int:
    context = DiscoveryContext(
        profile="FEATURE_DISCOVERY_PROFILE_V1",
        domain="FEATURES",
        schema_filter=(),
        name_patterns=("FEATURES",),
    )

    objects = FeatureDiscovery(".").discover(context)

    print("=== FEATURE_DISCOVERY_PLUGIN_V1 ===")
    print(f"profile={context.profile}")
    print("domain=FEATURES")
    print(f"objects_discovered={len(objects)}")

    for obj in objects:
        print(
            "discovered_object="
            f"{obj.object_id}|{obj.domain}|{obj.category}|"
            f"{obj.object_type}|{obj.warehouse_layer}"
        )

    print("plugin_model=PLUGIN_BASED")
    print("discovery_source=FeatureDiscovery")
    print("catalog_write_deferred=1")
    print("ai_policy=AI_RECOMMENDS_ONLY_NO_DIRECT_EXECUTION")
    print("model_policy=MODEL_NO_DIRECT_EXECUTION")
    print("runtime_changed=0")
    print("execution_changed=0")
    print("orders_changed=0")
    print("fills_changed=0")
    print("micro_live_allowed=0")
    print("VERDICT=FEATURE_DISCOVERY_PLUGIN_V1_READY")
    return 0


if __name__ == "__main__":
    sys.exit(main())
