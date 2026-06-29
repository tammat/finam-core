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
                WHERE domain='FEATURES'
            """)
            total = int(cur.fetchone()["cnt"])

            cur.execute("""
                SELECT count(*)::bigint AS cnt
                FROM warehouse.analytics_asset_catalog_v1
                WHERE domain='FEATURES'
                  AND coalesce(object_id,'') <> ''
                  AND coalesce(object_name,'') <> ''
                  AND coalesce(category,'') <> ''
                  AND payload->>'discovery_source'='FeatureDiscovery'
            """)
            valid_required = int(cur.fetchone()["cnt"])

            cur.execute("""
                SELECT count(*)::bigint AS cnt
                FROM (
                    SELECT object_id
                    FROM warehouse.analytics_asset_catalog_v1
                    WHERE domain='FEATURES'
                    GROUP BY object_id
                    HAVING count(*) > 1
                ) d
            """)
            duplicate_object_ids = int(cur.fetchone()["cnt"])

            cur.execute("""
                SELECT count(*)::bigint AS cnt
                FROM warehouse.analytics_asset_catalog_v1
                WHERE domain='FEATURES'
                  AND health_light='GREEN'
            """)
            green = int(cur.fetchone()["cnt"])

    ok = total >= 1 and valid_required == total and duplicate_object_ids == 0 and green == total

    print("=== FEATURE_DISCOVERY_VALIDATION_V1 ===")
    print("domain=FEATURES")
    print(f"catalog_total={total}")
    print(f"required_fields_valid={valid_required}")
    print(f"duplicate_object_ids={duplicate_object_ids}")
    print(f"green_objects={green}")
    print("validation_policy=REQUIRED_FIELDS_NO_DUPLICATES_GREEN_HEALTH")
    print("feature_profile_valid=1" if ok else "feature_profile_valid=0")
    print("runtime_changed=0")
    print("execution_changed=0")
    print("orders_changed=0")
    print("fills_changed=0")
    print("micro_live_allowed=0")
    print("VERDICT=FEATURE_DISCOVERY_VALIDATION_V1_READY" if ok else "VERDICT=FEATURE_DISCOVERY_VALIDATION_V1_FAILED")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
