#!/usr/bin/env python3
from __future__ import annotations

import os
import sys
import psycopg2
import psycopg2.extras

from marketcore.registry.json import dumps_payload


CANONICAL_AI_COMPONENTS = [
    ("AI_REGISTRY_MANAGER", "AI Registry Manager", "AI_AGENT", "Управление AI Registry"),
    ("AI_KNOWLEDGE_GRAPH_AGENT", "AI Knowledge Graph Agent", "AI_AGENT", "Работа с Knowledge Graph"),
    ("AI_RESEARCH_ASSISTANT", "AI Research Assistant", "AI_AGENT", "Помощник исследований"),
    ("AI_DATA_QUALITY_AGENT", "AI Data Quality Agent", "AI_AGENT", "Контроль качества данных"),
    ("AI_RUNTIME_GUARD", "AI Runtime Guard", "AI_POLICY", "Запрет прямого исполнения"),
    ("AI_GRAPH_REQUIRED", "AI Graph Required", "AI_POLICY", "Обязательное использование Knowledge Graph"),
    ("AI_MARKET_KNOWLEDGE_POLICY", "AI Market Knowledge Policy", "AI_POLICY", "AI не хранит знания о рынке"),
    ("AI_RECOMMENDATION_ONLY", "AI Recommendation Only", "AI_POLICY", "AI только рекомендует"),
    ("AI_EXPLAINABILITY", "AI Explainability", "AI_CAPABILITY", "Объяснение решений через Graph"),
    ("AI_REGISTRY_MANAGEMENT", "AI Registry Management", "AI_CAPABILITY", "Работа с Registry"),
]


def db_url() -> str:
    return os.getenv("DATABASE_URL", "postgresql:///finam_core")


def main() -> int:
    changed = 0

    with psycopg2.connect(db_url()) as conn:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            for code, name, ai_type, description in CANONICAL_AI_COMPONENTS:
                payload = dumps_payload({
                    "bootstrap_policy": "AI_BOOTSTRAP_POLICY_V1",
                    "registry_framework_version": "V1",
                    "domain_types_version": "V1",
                    "discovery_used": False,
                    "market_knowledge_stored": False,
                })

                cur.execute(
                    """
                    INSERT INTO warehouse.ai_registry_v1 (
                        ai_code,
                        ai_name,
                        ai_type,
                        version,
                        status,
                        maturity_level,
                        description,
                        source_of_truth,
                        owner_module,
                        execution_policy,
                        market_knowledge_policy,
                        approved_for_live,
                        approved_for_paper,
                        approved_for_shadow,
                        prompt_allowed,
                        tool_allowed,
                        graph_required,
                        payload
                    )
                    VALUES (
                        %s, %s, %s,
                        'v1',
                        'REGISTERED',
                        'RESEARCH',
                        %s,
                        'AI_REGISTRY_BUILDER_V1',
                        'marketcore.ai',
                        'AI_RECOMMENDS_ONLY_NO_DIRECT_EXECUTION',
                        'AI_REGISTRY_STORES_AI_KNOWLEDGE_ONLY',
                        false,
                        false,
                        false,
                        false,
                        false,
                        true,
                        %s::jsonb
                    )
                    ON CONFLICT (ai_code) DO UPDATE SET
                        ai_name=EXCLUDED.ai_name,
                        ai_type=EXCLUDED.ai_type,
                        description=EXCLUDED.description,
                        source_of_truth=EXCLUDED.source_of_truth,
                        execution_policy=EXCLUDED.execution_policy,
                        market_knowledge_policy=EXCLUDED.market_knowledge_policy,
                        approved_for_live=false,
                        graph_required=true,
                        payload=EXCLUDED.payload,
                        updated_at=now()
                    """,
                    (code, name, ai_type, description, payload),
                )
                changed += cur.rowcount

            conn.commit()

            cur.execute("SELECT count(*)::int AS total FROM warehouse.ai_registry_v1")
            total = int(cur.fetchone()["total"])

            cur.execute("""
                SELECT ai_type, count(*)::int AS cnt
                FROM warehouse.ai_registry_v1
                GROUP BY ai_type
                ORDER BY ai_type
            """)
            type_rows = cur.fetchall()

            cur.execute("""
                SELECT count(*)::int AS unsafe
                FROM warehouse.ai_registry_v1
                WHERE approved_for_live=true
                   OR execution_policy <> 'AI_RECOMMENDS_ONLY_NO_DIRECT_EXECUTION'
                   OR market_knowledge_policy <> 'AI_REGISTRY_STORES_AI_KNOWLEDGE_ONLY'
            """)
            unsafe = int(cur.fetchone()["unsafe"])

    print("=== AI_REGISTRY_BUILDER_V1 ===")
    print(f"registry_rows_changed={changed}")
    print(f"ai_registry_total={total}")
    for row in type_rows:
        print(f"type_count={row['ai_type']}:{row['cnt']}")
    print(f"unsafe_ai_rows={unsafe}")
    print("framework=REGISTRY_FRAMEWORK_V1")
    print("bootstrap_policy=AI_BOOTSTRAP_POLICY_V1")
    print("discovery_used=0")
    print("market_knowledge_stored=0")
    print("execution_policy=AI_RECOMMENDS_ONLY_NO_DIRECT_EXECUTION")
    print("market_knowledge_policy=AI_REGISTRY_STORES_AI_KNOWLEDGE_ONLY")
    print("runtime_changed=0")
    print("execution_changed=0")
    print("orders_changed=0")
    print("fills_changed=0")
    print("micro_live_allowed=0")
    print("VERDICT=AI_REGISTRY_BUILDER_V1_READY" if total == 10 and unsafe == 0 else "VERDICT=AI_REGISTRY_BUILDER_V1_FAILED")
    return 0 if total == 10 and unsafe == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
