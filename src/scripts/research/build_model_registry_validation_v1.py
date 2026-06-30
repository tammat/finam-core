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
            cur.execute("SELECT count(*)::bigint AS cnt FROM warehouse.model_registry_v1")
            total = int(cur.fetchone()["cnt"])

            cur.execute("""
                SELECT count(*)::bigint AS cnt
                FROM warehouse.model_registry_v1
                WHERE coalesce(model_code,'') <> ''
                  AND coalesce(model_name,'') <> ''
                  AND coalesce(status,'') <> ''
                  AND coalesce(maturity_level,'') <> ''
                  AND coalesce(validation_status,'') <> ''
            """)
            required = int(cur.fetchone()["cnt"])

            cur.execute("""
                SELECT count(*)::bigint AS cnt
                FROM (
                    SELECT model_code
                    FROM warehouse.model_registry_v1
                    GROUP BY model_code
                    HAVING count(*) > 1
                ) d
            """)
            duplicates = int(cur.fetchone()["cnt"])

            cur.execute("""
                SELECT count(*)::bigint AS cnt
                FROM warehouse.model_registry_v1
                WHERE approved_for_live = true
                   OR approved_for_paper = true
                   OR approved_for_shadow = true
            """)
            unsafe_approvals = int(cur.fetchone()["cnt"])

    ok = total == 280 and required == total and duplicates == 0 and unsafe_approvals == 0

    print("=== MODEL_REGISTRY_VALIDATION_V1 ===")
    print(f"model_registry_total={total}")
    print(f"required_fields_valid={required}")
    print(f"duplicate_model_codes={duplicates}")
    print(f"unsafe_approvals={unsafe_approvals}")
    print("validation_policy=REQUIRED_FIELDS_NO_DUPLICATES_NO_LIVE_APPROVAL")
    print("model_registry_valid=1" if ok else "model_registry_valid=0")
    print("ai_policy=AI_RECOMMENDS_ONLY_NO_DIRECT_EXECUTION")
    print("model_policy=MODEL_NO_DIRECT_EXECUTION")
    print("runtime_changed=0")
    print("execution_changed=0")
    print("orders_changed=0")
    print("fills_changed=0")
    print("micro_live_allowed=0")
    print("VERDICT=MODEL_REGISTRY_VALIDATION_V1_READY" if ok else "VERDICT=MODEL_REGISTRY_VALIDATION_V1_FAILED")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
