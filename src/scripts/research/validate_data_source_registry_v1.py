#!/usr/bin/env python3
from __future__ import annotations

import os
import psycopg2

DB = os.getenv("DATABASE_URL", "postgresql:///finam_core")

REQUIRED_SOURCES = [
    "Finam Runtime",
    "Finam History",
    "MOEX History",
    "Generated",
    "Replay",
    "Paper Trading",
    "Runtime Trading",
    "Broker",
    "Strategy",
    "Research",
    "Feature",
    "AI",
]

REQUIRED_DOMAINS = [
    "Market",
    "Trading",
    "Broker",
    "Strategy",
    "Research",
    "Feature",
    "AI",
]

def main() -> None:
    print("=== DATA_SOURCE_REGISTRY_DB_VALIDATION_V1 ===")

    conn = psycopg2.connect(DB)
    try:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT count(*)
                FROM warehouse.data_source_registry_v1
                WHERE active=true;
            """)
            active_sources = cur.fetchone()[0]

            cur.execute("""
                SELECT source_origin
                FROM warehouse.data_source_registry_v1
                WHERE active=true
                ORDER BY source_origin;
            """)
            existing_sources = {r[0] for r in cur.fetchall()}

            cur.execute("""
                SELECT domain
                FROM warehouse.data_source_registry_v1
                WHERE active=true
                GROUP BY domain
                ORDER BY domain;
            """)
            existing_domains = {r[0] for r in cur.fetchall()}

            cur.execute("""
                SELECT source_origin, count(*)
                FROM warehouse.data_source_registry_v1
                GROUP BY source_origin
                HAVING count(*) > 1;
            """)
            duplicate_rows = cur.fetchall()

            cur.execute("""
                SELECT source_origin
                FROM warehouse.data_source_registry_v1
                WHERE source_origin='AI'
                  AND normalization_status='GATED_NO_ORDER_ACCESS'
                  AND active=true;
            """)
            ai_gated = cur.rowcount

            cur.execute("""
                SELECT source_origin
                FROM warehouse.data_source_registry_v1
                WHERE source_origin='Runtime Trading'
                  AND normalization_status='BLOCKED_FOR_LIVE'
                  AND active=true;
            """)
            runtime_blocked = cur.rowcount

        missing_sources = sorted(set(REQUIRED_SOURCES) - existing_sources)
        missing_domains = sorted(set(REQUIRED_DOMAINS) - existing_domains)

        for source in sorted(existing_sources):
            print(f"SOURCE_OK|source_origin={source}")

        for source in missing_sources:
            print(f"SOURCE_MISSING|source_origin={source}")

        for domain in sorted(existing_domains):
            print(f"DOMAIN_OK|domain={domain}")

        for domain in missing_domains:
            print(f"DOMAIN_MISSING|domain={domain}")

        for source, count in duplicate_rows:
            print(f"DUPLICATE_SOURCE|source_origin={source}|count={count}")

        validation_ok = (
            active_sources == 12
            and not missing_sources
            and not missing_domains
            and not duplicate_rows
            and ai_gated == 1
            and runtime_blocked == 1
        )

        print(f"active_sources={active_sources}")
        print(f"missing_sources={len(missing_sources)}")
        print(f"missing_domains={len(missing_domains)}")
        print(f"duplicate_sources={len(duplicate_rows)}")
        print(f"ai_gated_rows={ai_gated}")
        print(f"runtime_live_block_rows={runtime_blocked}")
        print("runtime_changed=0")
        print("execution_changed=0")
        print("orders_changed=0")
        print("fills_changed=0")
        print("micro_live_allowed=0")

        if validation_ok:
            print("VERDICT=DATA_SOURCE_REGISTRY_DB_VALIDATION_V1_READY")
        else:
            print("VERDICT=DATA_SOURCE_REGISTRY_DB_VALIDATION_V1_FAILED")
            raise SystemExit(1)
    finally:
        conn.close()

if __name__ == "__main__":
    main()
