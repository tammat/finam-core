#!/usr/bin/env python3
from __future__ import annotations

import os
import psycopg2

DB = os.getenv("DATABASE_URL", "postgresql:///finam_core")

SOURCES = [
    ("Market", "Finam Runtime", "finam_runtime", "bar", "market_bar", "READY", "stream", "hot+cold", "runtime,research,strategy", False),
    ("Market", "Finam History", "finam_history", "bar", "market_bar", "READY", "batch", "cold", "research,feature", True),
    ("Market", "MOEX History", "moex_history", "bar", "market_bar", "PLANNED", "batch", "cold", "research,feature", True),
    ("Research", "Generated", "research_generator", "synthetic_event", "research_event", "READY", "batch", "cold", "research", True),
    ("Research", "Replay", "replay_engine", "trade_replay", "replay_trade", "READY", "batch", "cold", "research,edge", True),
    ("Trading", "Paper Trading", "paper_execution", "paper_fill", "paper_trade", "READY", "event", "hot+cold", "portfolio,risk,research", True),
    ("Trading", "Runtime Trading", "runtime_execution", "runtime_fill", "runtime_trade", "BLOCKED_FOR_LIVE", "event", "hot+cold", "portfolio,risk,audit", False),
    ("Broker", "Broker", "finam_broker", "broker_event", "broker_trade", "PARTIAL", "event", "hot+cold", "execution,portfolio,audit", False),
    ("Strategy", "Strategy", "strategy_engine", "signal", "strategy_signal", "READY", "event", "hot+cold", "risk,research,execution", True),
    ("Research", "Research", "research_pipeline", "research_result", "research_candidate", "READY", "batch", "cold", "edge,governance", True),
    ("Feature", "Feature", "feature_builder", "feature", "feature_vector", "READY", "batch", "cold", "strategy,ai,research", True),
    ("AI", "AI", "ai_layer", "ai_score", "ai_recommendation", "GATED_NO_ORDER_ACCESS", "batch", "cold", "research,governance", True),
]

DDL = """
CREATE TABLE IF NOT EXISTS warehouse.data_source_registry_v1 (
    id bigserial PRIMARY KEY,
    domain text NOT NULL,
    source_origin text NOT NULL UNIQUE,
    producer text NOT NULL,
    entity_type text NOT NULL,
    canonical_entity text NOT NULL,
    normalization_status text NOT NULL,
    update_mode text NOT NULL,
    retention_policy text NOT NULL,
    consumer text NOT NULL,
    is_reproducible boolean NOT NULL,
    active boolean NOT NULL DEFAULT true,
    created_at timestamptz NOT NULL DEFAULT now(),
    updated_at timestamptz NOT NULL DEFAULT now()
);
"""

UPSERT = """
INSERT INTO warehouse.data_source_registry_v1 (
    domain,
    source_origin,
    producer,
    entity_type,
    canonical_entity,
    normalization_status,
    update_mode,
    retention_policy,
    consumer,
    is_reproducible
)
VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
ON CONFLICT (source_origin)
DO UPDATE SET
    domain=EXCLUDED.domain,
    producer=EXCLUDED.producer,
    entity_type=EXCLUDED.entity_type,
    canonical_entity=EXCLUDED.canonical_entity,
    normalization_status=EXCLUDED.normalization_status,
    update_mode=EXCLUDED.update_mode,
    retention_policy=EXCLUDED.retention_policy,
    consumer=EXCLUDED.consumer,
    is_reproducible=EXCLUDED.is_reproducible,
    active=true,
    updated_at=now();
"""

def main() -> None:
    print("=== DATA_SOURCE_REGISTRY_DB_PERSIST_V1 ===")

    conn = psycopg2.connect(DB)
    try:
        with conn.cursor() as cur:
            cur.execute("CREATE SCHEMA IF NOT EXISTS warehouse;")
            cur.execute(DDL)

            for row in SOURCES:
                cur.execute(UPSERT, row)

            cur.execute("SELECT count(*) FROM warehouse.data_source_registry_v1 WHERE active=true;")
            active_sources = cur.fetchone()[0]

            cur.execute("""
                SELECT count(*)
                FROM warehouse.data_source_registry_v1
                WHERE source_origin='AI'
                  AND normalization_status='GATED_NO_ORDER_ACCESS';
            """)
            ai_gated = cur.fetchone()[0]

        conn.commit()

        print(f"sources_persisted={len(SOURCES)}")
        print(f"active_sources={active_sources}")
        print(f"ai_gated_rows={ai_gated}")
        print("runtime_changed=0")
        print("execution_changed=0")
        print("orders_changed=0")
        print("fills_changed=0")
        print("micro_live_allowed=0")
        print("VERDICT=DATA_SOURCE_REGISTRY_DB_PERSIST_V1_READY")
    finally:
        conn.close()

if __name__ == "__main__":
    main()
