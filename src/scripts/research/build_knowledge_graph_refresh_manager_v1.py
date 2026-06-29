#!/usr/bin/env python3
from __future__ import annotations

import os
import sys
import time
import psycopg2
import psycopg2.extras


LOCK_KEY = 2026062901


def db_url() -> str:
    return os.getenv("DATABASE_URL", "postgresql:///finam_core")


def main() -> int:
    started = time.monotonic()

    with psycopg2.connect(db_url()) as conn:
        conn.autocommit = False
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute("SELECT pg_try_advisory_lock(%s) AS locked", (LOCK_KEY,))
            locked = bool(cur.fetchone()["locked"])

            if not locked:
                print("=== KNOWLEDGE_GRAPH_REFRESH_MANAGER_V1 ===")
                print("refresh_lock=BUSY")
                print("refresh_done=0")
                print("runtime_changed=0")
                print("execution_changed=0")
                print("orders_changed=0")
                print("fills_changed=0")
                print("micro_live_allowed=0")
                print("VERDICT=KNOWLEDGE_GRAPH_REFRESH_MANAGER_V1_BUSY")
                return 2

            try:
                cur.execute("REFRESH MATERIALIZED VIEW warehouse.kg_path_v1")
                cur.execute("REFRESH MATERIALIZED VIEW warehouse.kg_statistics_v1")
                conn.commit()

                cur.execute("SELECT count(*)::bigint AS cnt FROM warehouse.kg_node_v1")
                nodes = int(cur.fetchone()["cnt"])

                cur.execute("SELECT count(*)::bigint AS cnt FROM warehouse.kg_edge_v1")
                edges = int(cur.fetchone()["cnt"])

                cur.execute("SELECT count(*)::bigint AS cnt FROM warehouse.kg_path_v1")
                paths = int(cur.fetchone()["cnt"])

                cur.execute("""
                    SELECT total_nodes, total_edges, node_types, relationship_types,
                           isolated_nodes, not_validated_edges
                    FROM warehouse.kg_statistics_v1
                """)
                stats = cur.fetchone()

                duration_ms = int((time.monotonic() - started) * 1000)

                ok = (
                    nodes == int(stats["total_nodes"])
                    and edges == int(stats["total_edges"])
                    and paths == 632
                    and int(stats["not_validated_edges"]) == 0
                )

                print("=== KNOWLEDGE_GRAPH_REFRESH_MANAGER_V1 ===")
                print("refresh_lock=ACQUIRED")
                print("refresh_done=1")
                print(f"kg_node_rows={nodes}")
                print(f"kg_edge_rows={edges}")
                print(f"kg_path_rows={paths}")
                print(f"node_types={stats['node_types']}")
                print(f"relationship_types={stats['relationship_types']}")
                print(f"isolated_nodes={stats['isolated_nodes']}")
                print(f"not_validated_edges={stats['not_validated_edges']}")
                print(f"refresh_duration_ms={duration_ms}")
                print("refresh_policy=ADVISORY_LOCK_PLUS_MATERIALIZED_VIEW_REFRESH")
                print("source_policy=REGISTRY_AND_RELATIONSHIPS_ARE_SOURCE_OF_TRUTH")
                print("runtime_changed=0")
                print("execution_changed=0")
                print("orders_changed=0")
                print("fills_changed=0")
                print("micro_live_allowed=0")
                print("VERDICT=KNOWLEDGE_GRAPH_REFRESH_MANAGER_V1_READY" if ok else "VERDICT=KNOWLEDGE_GRAPH_REFRESH_MANAGER_V1_FAILED")
                return 0 if ok else 1

            finally:
                cur.execute("SELECT pg_advisory_unlock(%s)", (LOCK_KEY,))
                conn.commit()


if __name__ == "__main__":
    sys.exit(main())
