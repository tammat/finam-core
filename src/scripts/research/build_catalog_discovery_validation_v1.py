#!/usr/bin/env python3
from __future__ import annotations

import os
import sys
import psycopg2
import psycopg2.extras


def db_url() -> str:
    return os.getenv("DATABASE_URL", "postgresql:///finam_core")


def main() -> int:
    with psycopg2.connect(db_url()) as conn:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute("""
                SELECT count(*)::bigint AS cnt
                FROM warehouse.analytics_asset_catalog_v1
                WHERE domain='WORKFLOW'
            """)
            total = int(cur.fetchone()["cnt"])

            cur.execute("""
                SELECT count(*)::bigint AS cnt
                FROM warehouse.analytics_asset_catalog_v1
                WHERE domain='WORKFLOW'
                  AND coalesce(object_id,'') <> ''
                  AND coalesce(object_name,'') <> ''
                  AND coalesce(category,'') <> ''
                  AND coalesce(payload->>'discovery_source','') <> ''
            """)
            valid_required = int(cur.fetchone()["cnt"])

            cur.execute("""
                SELECT count(*)::bigint AS cnt
                FROM (
                    SELECT object_id
                    FROM warehouse.analytics_asset_catalog_v1
                    WHERE domain='WORKFLOW'
                    GROUP BY object_id
                    HAVING count(*) > 1
                ) d
            """)
            duplicate_object_ids = int(cur.fetchone()["cnt"])

            cur.execute("""
                SELECT count(*)::bigint AS cnt
                FROM warehouse.analytics_asset_catalog_v1
                WHERE domain='WORKFLOW'
                  AND health_light='GREEN'
            """)
            green = int(cur.fetchone()["cnt"])

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

            cur.execute("""
                SELECT warehouse_layer, count(*) AS cnt
                FROM warehouse.analytics_asset_catalog_v1
                WHERE domain='WORKFLOW'
                GROUP BY warehouse_layer
                ORDER BY warehouse_layer
            """)
            layers = cur.fetchall()

    source_map = {r["source"]: int(r["cnt"]) for r in sources}
    ok = (
        total >= 82
        and valid_required == total
        and duplicate_object_ids == 0
        and green == total
        and source_map.get("PostgresDiscovery", 0) >= 16
        and source_map.get("PythonDiscovery", 0) >= 1 and source_map.get("BashDiscovery", 0) >= 1
    )

    print("=== CATALOG_DISCOVERY_VALIDATION_V1_1 ===")
    print(f"domain=WORKFLOW")
    print(f"catalog_total={total}")
    print(f"required_fields_valid={valid_required}")
    print(f"duplicate_object_ids={duplicate_object_ids}")
    print(f"green_objects={green}")

    for r in sources:
        print(f"source_count={r['source']}:{r['cnt']}")

    for r in categories:
        print(f"category_count={r['category']}:{r['cnt']}")

    for r in layers:
        print(f"layer_count={r['warehouse_layer']}:{r['cnt']}")

    print("validation_policy=REQUIRED_FIELDS_NO_DUPLICATES_GREEN_HEALTH")
    print("workflow_profile_valid=1" if ok else "workflow_profile_valid=0")
    print("runtime_changed=0")
    print("execution_changed=0")
    print("orders_changed=0")
    print("fills_changed=0")
    print("micro_live_allowed=0")
    print("VERDICT=CATALOG_DISCOVERY_VALIDATION_V1_1_READY" if ok else "VERDICT=CATALOG_DISCOVERY_VALIDATION_V1_1_FAILED")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
