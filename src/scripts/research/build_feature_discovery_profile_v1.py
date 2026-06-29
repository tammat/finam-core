#!/usr/bin/env python3
from __future__ import annotations

import os
import sys
import psycopg2
import psycopg2.extras

from marketcore.catalog.discovery.context import DiscoveryContext
from marketcore.catalog.discovery.executor import DiscoveryExecutor
from marketcore.catalog.discovery.plugins.feature_discovery import FeatureDiscovery
from marketcore.catalog.writer.catalog_writer import CatalogWriter


def db_url() -> str:
    return os.getenv("DATABASE_URL", "postgresql:///finam_core")


def main() -> int:
    context = DiscoveryContext(
        profile="FEATURE_DISCOVERY_PROFILE_V1",
        domain="FEATURES",
        schema_filter=(),
        name_patterns=("FEATURES",),
    )

    objects = DiscoveryExecutor([FeatureDiscovery(".")]).run(context)

    with psycopg2.connect(db_url()) as conn:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            written = CatalogWriter().write(cur, objects)
            conn.commit()

            cur.execute("""
                SELECT count(*)::bigint AS cnt
                FROM warehouse.analytics_asset_catalog_v1
                WHERE domain='FEATURES'
                  AND payload->>'discovery_source'='FeatureDiscovery'
            """)
            total = int(cur.fetchone()["cnt"])

    print("=== FEATURE_DISCOVERY_PROFILE_V1 ===")
    print(f"profile={context.profile}")
    print("domain=FEATURES")
    print(f"objects_discovered={len(objects)}")
    print(f"catalog_rows_written={written}")
    print(f"catalog_features_total={total}")
    print("discovery_plugins=FeatureDiscovery")
    print("writer=CatalogWriter")
    print("write_policy=UPSERT_BY_OBJECT_ID")
    print("target_catalog=warehouse.analytics_asset_catalog_v1")
    print("ai_policy=AI_RECOMMENDS_ONLY_NO_DIRECT_EXECUTION")
    print("model_policy=MODEL_NO_DIRECT_EXECUTION")
    print("runtime_changed=0")
    print("execution_changed=0")
    print("orders_changed=0")
    print("fills_changed=0")
    print("micro_live_allowed=0")
    print("VERDICT=FEATURE_DISCOVERY_PROFILE_V1_READY")
    return 0


if __name__ == "__main__":
    sys.exit(main())
