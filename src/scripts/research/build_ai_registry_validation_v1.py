#!/usr/bin/env python3
from __future__ import annotations

import os
import sys
import psycopg2
import psycopg2.extras

from marketcore.registry.lifecycle import REGISTRY_MATURITY_LEVELS, REGISTRY_STATUSES


def db_url() -> str:
    return os.getenv("DATABASE_URL", "postgresql:///finam_core")


def scalar(cur, sql: str) -> int:
    cur.execute(sql)
    return int(cur.fetchone()["v"])


def main() -> int:
    with psycopg2.connect(db_url()) as conn:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            total = scalar(cur, "SELECT count(*)::int AS v FROM warehouse.ai_registry_v1")

            required_fields_valid = scalar(cur, """
                SELECT count(*)::int AS v
                FROM warehouse.ai_registry_v1
                WHERE btrim(ai_code) <> ''
                  AND btrim(ai_name) <> ''
                  AND btrim(ai_type) <> ''
                  AND btrim(version) <> ''
                  AND btrim(status) <> ''
                  AND btrim(maturity_level) <> ''
                  AND btrim(source_of_truth) <> ''
                  AND btrim(owner_module) <> ''
                  AND btrim(execution_policy) <> ''
                  AND btrim(market_knowledge_policy) <> ''
            """)

            duplicate_ai_codes = scalar(cur, """
                SELECT count(*)::int AS v
                FROM (
                    SELECT ai_code
                    FROM warehouse.ai_registry_v1
                    GROUP BY ai_code
                    HAVING count(*) > 1
                ) d
            """)

            status_values = ",".join("'" + v + "'" for v in REGISTRY_STATUSES)
            maturity_values = ",".join("'" + v + "'" for v in REGISTRY_MATURITY_LEVELS)

            status_valid = scalar(cur, f"""
                SELECT count(*)::int AS v
                FROM warehouse.ai_registry_v1
                WHERE status IN ({status_values})
            """)

            maturity_valid = scalar(cur, f"""
                SELECT count(*)::int AS v
                FROM warehouse.ai_registry_v1
                WHERE maturity_level IN ({maturity_values})
            """)

            execution_policy_valid = scalar(cur, """
                SELECT count(*)::int AS v
                FROM warehouse.ai_registry_v1
                WHERE execution_policy='AI_RECOMMENDS_ONLY_NO_DIRECT_EXECUTION'
            """)

            market_policy_valid = scalar(cur, """
                SELECT count(*)::int AS v
                FROM warehouse.ai_registry_v1
                WHERE market_knowledge_policy='AI_REGISTRY_STORES_AI_KNOWLEDGE_ONLY'
            """)

            graph_required_valid = scalar(cur, """
                SELECT count(*)::int AS v
                FROM warehouse.ai_registry_v1
                WHERE graph_required=true
            """)

            bootstrap_policy_valid = scalar(cur, """
                SELECT count(*)::int AS v
                FROM warehouse.ai_registry_v1
                WHERE payload->>'bootstrap_policy'='AI_BOOTSTRAP_POLICY_V1'
                  AND coalesce((payload->>'discovery_used')::boolean, true)=false
                  AND coalesce((payload->>'market_knowledge_stored')::boolean, true)=false
            """)

            framework_version_valid = scalar(cur, """
                SELECT count(*)::int AS v
                FROM warehouse.ai_registry_v1
                WHERE payload->>'registry_framework_version'='V1'
            """)

            domain_types_version_valid = scalar(cur, """
                SELECT count(*)::int AS v
                FROM warehouse.ai_registry_v1
                WHERE payload->>'domain_types_version'='V1'
            """)

            description_valid = scalar(cur, """
                SELECT count(*)::int AS v
                FROM warehouse.ai_registry_v1
                WHERE btrim(description) <> ''
            """)

            forbidden_market_fields = scalar(cur, """
                SELECT count(*)::int AS v
                FROM warehouse.ai_registry_v1
                WHERE payload ? 'feature_code'
                   OR payload ? 'model_code'
                   OR payload ? 'experiment_code'
                   OR payload ? 'dataset_code'
                   OR payload::text ILIKE '%feature_code%'
                   OR payload::text ILIKE '%model_code%'
                   OR payload::text ILIKE '%experiment_code%'
                   OR payload::text ILIKE '%dataset_code%'
            """)

            unsafe_live_rows = scalar(cur, """
                SELECT count(*)::int AS v
                FROM warehouse.ai_registry_v1
                WHERE approved_for_live=true
                   OR execution_policy <> 'AI_RECOMMENDS_ONLY_NO_DIRECT_EXECUTION'
                   OR market_knowledge_policy <> 'AI_REGISTRY_STORES_AI_KNOWLEDGE_ONLY'
            """)

    ok = (
        total == 10
        and required_fields_valid == total
        and duplicate_ai_codes == 0
        and status_valid == total
        and maturity_valid == total
        and execution_policy_valid == total
        and market_policy_valid == total
        and graph_required_valid == total
        and bootstrap_policy_valid == total
        and framework_version_valid == total
        and domain_types_version_valid == total
        and description_valid == total
        and forbidden_market_fields == 0
        and unsafe_live_rows == 0
    )

    print("=== AI_REGISTRY_VALIDATION_V1 ===")
    print(f"ai_registry_total={total}")
    print(f"required_fields_valid={required_fields_valid}")
    print(f"duplicate_ai_codes={duplicate_ai_codes}")
    print(f"status_valid={status_valid}")
    print(f"maturity_valid={maturity_valid}")
    print(f"execution_policy_valid={execution_policy_valid}")
    print(f"market_policy_valid={market_policy_valid}")
    print(f"graph_required_valid={graph_required_valid}")
    print(f"bootstrap_policy_valid={bootstrap_policy_valid}")
    print(f"framework_version_valid={framework_version_valid}")
    print(f"domain_types_version_valid={domain_types_version_valid}")
    print(f"description_valid={description_valid}")
    print(f"forbidden_market_fields={forbidden_market_fields}")
    print(f"unsafe_live_rows={unsafe_live_rows}")
    print("framework=REGISTRY_FRAMEWORK_V1")
    print("ai_policy=AI_REGISTRY_STORES_AI_KNOWLEDGE_ONLY")
    print("runtime_changed=0")
    print("execution_changed=0")
    print("orders_changed=0")
    print("fills_changed=0")
    print("micro_live_allowed=0")
    print("VERDICT=AI_REGISTRY_VALIDATION_V1_READY" if ok else "VERDICT=AI_REGISTRY_VALIDATION_V1_FAILED")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
