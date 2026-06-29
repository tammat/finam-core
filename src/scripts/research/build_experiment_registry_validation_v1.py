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
            cur.execute("SELECT count(*)::bigint AS cnt FROM warehouse.experiment_registry_v1")
            total = int(cur.fetchone()["cnt"])

            cur.execute("""
                SELECT count(*)::bigint AS cnt
                FROM warehouse.experiment_registry_v1
                WHERE coalesce(experiment_code,'') <> ''
                  AND coalesce(experiment_name,'') <> ''
                  AND coalesce(status,'') <> ''
                  AND coalesce(maturity_level,'') <> ''
                  AND coalesce(decision,'') <> ''
            """)
            required = int(cur.fetchone()["cnt"])

            cur.execute("""
                SELECT count(*)::bigint AS cnt
                FROM (
                    SELECT experiment_code
                    FROM warehouse.experiment_registry_v1
                    GROUP BY experiment_code
                    HAVING count(*) > 1
                ) d
            """)
            duplicates = int(cur.fetchone()["cnt"])

            cur.execute("""
                SELECT count(*)::bigint AS cnt
                FROM warehouse.experiment_registry_v1
                WHERE approved_for_live = true
                   OR approved_for_paper = true
                   OR approved_for_shadow = true
            """)
            unsafe_approvals = int(cur.fetchone()["cnt"])

    ok = total >= 1 and required == total and duplicates == 0 and unsafe_approvals == 0

    print("=== EXPERIMENT_REGISTRY_VALIDATION_V1 ===")
    print(f"experiment_registry_total={total}")
    print(f"required_fields_valid={required}")
    print(f"duplicate_experiment_codes={duplicates}")
    print(f"unsafe_approvals={unsafe_approvals}")
    print("политика_валидации=ОБЯЗАТЕЛЬНЫЕ_ПОЛЯ_БЕЗ_ДУБЛЕЙ_БЕЗ_LIVE_ДОПУСКА")
    print("experiment_registry_valid=1" if ok else "experiment_registry_valid=0")
    print("runtime_changed=0")
    print("execution_changed=0")
    print("orders_changed=0")
    print("fills_changed=0")
    print("micro_live_allowed=0")
    print("VERDICT=EXPERIMENT_REGISTRY_VALIDATION_V1_READY" if ok else "VERDICT=EXPERIMENT_REGISTRY_VALIDATION_V1_FAILED")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
