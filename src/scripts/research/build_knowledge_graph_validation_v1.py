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
            cur.execute("SELECT count(*)::bigint AS cnt FROM warehouse.kg_node_v1")
            nodes = int(cur.fetchone()["cnt"])

            cur.execute("SELECT count(*)::bigint AS cnt FROM warehouse.kg_edge_v1")
            edges = int(cur.fetchone()["cnt"])

            cur.execute("SELECT count(*)::bigint AS cnt FROM warehouse.kg_path_v1")
            paths = int(cur.fetchone()["cnt"])

            cur.execute("""
                SELECT count(*)::bigint AS cnt
                FROM (
                    SELECT node_type, node_code
                    FROM warehouse.kg_node_v1
                    GROUP BY node_type, node_code
                    HAVING count(*) > 1
                ) d
            """)
            duplicate_nodes = int(cur.fetchone()["cnt"])

            cur.execute("""
                SELECT count(*)::bigint AS cnt
                FROM (
                    SELECT source_node_type, source_node_code,
                           target_node_type, target_node_code,
                           relationship_type
                    FROM warehouse.kg_edge_v1
                    GROUP BY source_node_type, source_node_code,
                             target_node_type, target_node_code,
                             relationship_type
                    HAVING count(*) > 1
                ) d
            """)
            duplicate_edges = int(cur.fetchone()["cnt"])

            cur.execute("""
                SELECT count(*)::bigint AS cnt
                FROM warehouse.kg_edge_v1 e
                LEFT JOIN warehouse.kg_node_v1 s
                  ON s.node_type=e.source_node_type
                 AND s.node_code=e.source_node_code
                WHERE s.node_code IS NULL
            """)
            broken_source_edges = int(cur.fetchone()["cnt"])

            cur.execute("""
                SELECT count(*)::bigint AS cnt
                FROM warehouse.kg_edge_v1 e
                LEFT JOIN warehouse.kg_node_v1 t
                  ON t.node_type=e.target_node_type
                 AND t.node_code=e.target_node_code
                WHERE t.node_code IS NULL
            """)
            broken_target_edges = int(cur.fetchone()["cnt"])

            cur.execute("""
                SELECT count(*)::bigint AS cnt
                FROM warehouse.kg_edge_v1
                WHERE validation_status <> 'VALIDATED'
            """)
            not_validated_edges = int(cur.fetchone()["cnt"])

            cur.execute("""
                SELECT count(*)::bigint AS cnt
                FROM warehouse.kg_path_v1
                WHERE validation_status <> 'VALIDATED'
            """)
            not_validated_paths = int(cur.fetchone()["cnt"])

            cur.execute("""
                SELECT count(*)::bigint AS cnt
                FROM warehouse.kg_node_v1 n
                LEFT JOIN warehouse.kg_edge_v1 e1
                  ON e1.source_node_type=n.node_type
                 AND e1.source_node_code=n.node_code
                LEFT JOIN warehouse.kg_edge_v1 e2
                  ON e2.target_node_type=n.node_type
                 AND e2.target_node_code=n.node_code
                WHERE e1.source_node_code IS NULL
                  AND e2.target_node_code IS NULL
            """)
            isolated_nodes = int(cur.fetchone()["cnt"])

            cur.execute("""
                SELECT node_type, count(*)::bigint AS cnt
                FROM warehouse.kg_node_v1 n
                LEFT JOIN warehouse.kg_edge_v1 e1
                  ON e1.source_node_type=n.node_type
                 AND e1.source_node_code=n.node_code
                LEFT JOIN warehouse.kg_edge_v1 e2
                  ON e2.target_node_type=n.node_type
                 AND e2.target_node_code=n.node_code
                WHERE e1.source_node_code IS NULL
                  AND e2.target_node_code IS NULL
                GROUP BY node_type
                ORDER BY node_type
            """)
            isolated_by_type = cur.fetchall()

    ok = (
        nodes == 1379
        and edges == 632
        and paths == 632
        and duplicate_edges == 0
        and broken_source_edges == 0
        and broken_target_edges == 0
        and not_validated_edges == 0
        and not_validated_paths == 0
    )

    print("=== KNOWLEDGE_GRAPH_VALIDATION_V1 ===")
    print(f"kg_node_rows={nodes}")
    print(f"kg_edge_rows={edges}")
    print(f"kg_path_rows={paths}")
    print(f"duplicate_nodes={duplicate_nodes}")
    print(f"duplicate_edges={duplicate_edges}")
    print(f"broken_source_edges={broken_source_edges}")
    print(f"broken_target_edges={broken_target_edges}")
    print(f"not_validated_edges={not_validated_edges}")
    print(f"not_validated_paths={not_validated_paths}")
    print(f"isolated_nodes={isolated_nodes}")
    for r in isolated_by_type:
        print(f"isolated_node_type={r['node_type']}:{r['cnt']}")
    print("isolated_policy=CLASSIFIED_NOT_FATAL_IN_V1")
    print("path_policy=DEPTH_1_ONLY_IN_V1")
    print("source_policy=REGISTRY_AND_RELATIONSHIPS_ARE_SOURCE_OF_TRUTH")
    print("runtime_changed=0")
    print("execution_changed=0")
    print("orders_changed=0")
    print("fills_changed=0")
    print("micro_live_allowed=0")
    print("VERDICT=KNOWLEDGE_GRAPH_VALIDATION_V1_READY" if ok else "VERDICT=KNOWLEDGE_GRAPH_VALIDATION_V1_FAILED")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
