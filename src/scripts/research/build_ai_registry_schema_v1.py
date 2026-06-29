#!/usr/bin/env python3
from __future__ import annotations

import os
import sys
import psycopg2

from marketcore.registry.indexes import standard_registry_indexes_sql
from marketcore.registry.lifecycle import REGISTRY_MATURITY_LEVELS, REGISTRY_STATUSES, sql_check_in


AI_TYPES = (
    "AI_AGENT",
    "AI_PROMPT",
    "AI_POLICY",
    "AI_PIPELINE",
    "AI_WORKFLOW",
    "AI_CAPABILITY",
    "AI_EVALUATION",
    "AI_TEMPLATE",
)


def db_url() -> str:
    return os.getenv("DATABASE_URL", "postgresql:///finam_core")


def main() -> int:
    ddl = f"""
CREATE TABLE IF NOT EXISTS warehouse.ai_registry_v1 (
    id bigserial PRIMARY KEY,
    ai_code text NOT NULL,
    ai_name text NOT NULL,
    ai_type text NOT NULL,
    version text NOT NULL DEFAULT 'v1',
    status text NOT NULL DEFAULT 'DISCOVERED',
    maturity_level text NOT NULL DEFAULT 'RESEARCH',
    description text NOT NULL DEFAULT '',
    source_of_truth text NOT NULL DEFAULT 'AI_REGISTRY_V1',
    owner_module text NOT NULL DEFAULT 'marketcore.ai',
    execution_policy text NOT NULL DEFAULT 'AI_RECOMMENDS_ONLY_NO_DIRECT_EXECUTION',
    market_knowledge_policy text NOT NULL DEFAULT 'AI_REGISTRY_STORES_AI_KNOWLEDGE_ONLY',
    approved_for_live boolean NOT NULL DEFAULT false,
    approved_for_paper boolean NOT NULL DEFAULT false,
    approved_for_shadow boolean NOT NULL DEFAULT false,
    prompt_allowed boolean NOT NULL DEFAULT false,
    tool_allowed boolean NOT NULL DEFAULT false,
    graph_required boolean NOT NULL DEFAULT true,
    payload jsonb NOT NULL DEFAULT '{{}}'::jsonb,
    created_at timestamptz NOT NULL DEFAULT now(),
    updated_at timestamptz NOT NULL DEFAULT now(),
    CONSTRAINT ai_registry_v1_code_not_empty CHECK (btrim(ai_code) <> ''),
    CONSTRAINT ai_registry_v1_name_not_empty CHECK (btrim(ai_name) <> ''),
    CONSTRAINT ai_registry_v1_type_check CHECK (ai_type IN {sql_check_in(AI_TYPES)}),
    CONSTRAINT ai_registry_v1_status_check CHECK (status IN {sql_check_in(REGISTRY_STATUSES)}),
    CONSTRAINT ai_registry_v1_maturity_check CHECK (maturity_level IN {sql_check_in(REGISTRY_MATURITY_LEVELS)}),
    CONSTRAINT ai_registry_v1_no_direct_execution CHECK (execution_policy='AI_RECOMMENDS_ONLY_NO_DIRECT_EXECUTION'),
    CONSTRAINT ai_registry_v1_no_market_knowledge CHECK (market_knowledge_policy='AI_REGISTRY_STORES_AI_KNOWLEDGE_ONLY'),
    CONSTRAINT ai_registry_v1_no_live_approval CHECK (approved_for_live=false)
);

{standard_registry_indexes_sql(
    table="warehouse.ai_registry_v1",
    table_short_name="ai_registry_v1",
    code_column="ai_code",
    type_column="ai_type",
)}
CREATE INDEX IF NOT EXISTS idx_ai_registry_v1_execution_policy
ON warehouse.ai_registry_v1(execution_policy);

CREATE INDEX IF NOT EXISTS idx_ai_registry_v1_market_knowledge_policy
ON warehouse.ai_registry_v1(market_knowledge_policy);
"""

    with psycopg2.connect(db_url()) as conn:
        with conn.cursor() as cur:
            cur.execute(ddl)
            conn.commit()

            cur.execute("""
                SELECT count(*)::int
                FROM information_schema.columns
                WHERE table_schema='warehouse'
                  AND table_name='ai_registry_v1'
            """)
            columns = cur.fetchone()[0]

            cur.execute("""
                SELECT count(*)::int
                FROM pg_indexes
                WHERE schemaname='warehouse'
                  AND tablename='ai_registry_v1'
            """)
            indexes = cur.fetchone()[0]

            cur.execute("""
                SELECT EXISTS (
                    SELECT 1
                    FROM information_schema.tables
                    WHERE table_schema='warehouse'
                      AND table_name='ai_registry_v1'
                )
            """)
            exists = cur.fetchone()[0]

    print("=== AI_REGISTRY_SCHEMA_V1 ===")
    print("table=warehouse.ai_registry_v1")
    print(f"columns={columns}")
    print(f"indexes={indexes}")
    print("назначение=реестр_AI_компонентов_платформы")
    print("ai_types=" + ",".join(AI_TYPES))
    print("status_model=" + ",".join(REGISTRY_STATUSES))
    print("maturity_model=" + ",".join(REGISTRY_MATURITY_LEVELS))
    print("execution_policy=AI_RECOMMENDS_ONLY_NO_DIRECT_EXECUTION")
    print("market_knowledge_policy=AI_REGISTRY_STORES_AI_KNOWLEDGE_ONLY")
    print("source_policy=AI_REGISTRY_DOES_NOT_STORE_MARKET_KNOWLEDGE")
    print("framework=REGISTRY_FRAMEWORK_V1")
    print("runtime_changed=0")
    print("execution_changed=0")
    print("orders_changed=0")
    print("fills_changed=0")
    print("micro_live_allowed=0")
    print("VERDICT=AI_REGISTRY_SCHEMA_V1_READY")
    print(f"ai_registry_exists={str(exists).lower()}")
    print(f"ai_registry_columns={columns}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
