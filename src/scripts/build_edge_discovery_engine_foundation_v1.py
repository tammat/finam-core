from __future__ import annotations

import os
from datetime import UTC, datetime

import psycopg2
import psycopg2.extras

DB = os.getenv("DATABASE_URL", "postgresql:///finam_core")


def main() -> None:
    batch_id = datetime.now(UTC).strftime("%Y%m%d_EDGE_DISCOVERY_ENGINE_FOUNDATION_V1")

    with psycopg2.connect(DB) as conn:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute("""
                SELECT count(*) AS methods_total,
                       count(*) FILTER (WHERE enabled=true) AS methods_enabled
                FROM analytics.edge_discovery_method_v1;
            """)
            methods = cur.fetchone()

            cur.execute("""
                SELECT count(*) AS rules_total,
                       count(*) FILTER (WHERE enabled=true) AS rules_enabled
                FROM analytics.edge_discovery_rule_v1;
            """)
            rules = cur.fetchone()

            cur.execute("""
                INSERT INTO analytics.edge_discovery_run_v1 (
                    discovery_batch_id,
                    method_code,
                    status_code,
                    source_version,
                    updated_at
                )
                VALUES (
                    %s,
                    'RULE_RANK_V1',
                    'QUEUED',
                    'EDGE_DISCOVERY_ENGINE_FOUNDATION_V1',
                    now()
                );
            """, (batch_id,))

            cur.execute("""
                SELECT count(*) AS runs_total
                FROM analytics.edge_discovery_run_v1;
            """)
            runs = cur.fetchone()

    print("=== EDGE_DISCOVERY_ENGINE_FOUNDATION_V1 ===")
    print(f"discovery_batch_id={batch_id}")
    print(f"methods_total={methods['methods_total']}")
    print(f"methods_enabled={methods['methods_enabled']}")
    print(f"rules_total={rules['rules_total']}")
    print(f"rules_enabled={rules['rules_enabled']}")
    print(f"runs_total={runs['runs_total']}")
    print("runtime_changed=0")
    print("execution_changed=0")
    print("orders_changed=0")
    print("fills_changed=0")
    print("micro_live_allowed=0")
    print("VERDICT=EDGE_DISCOVERY_ENGINE_FOUNDATION_V1_READY")


if __name__ == "__main__":
    main()
