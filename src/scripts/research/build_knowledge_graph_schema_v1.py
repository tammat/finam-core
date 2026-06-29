#!/usr/bin/env python3
from __future__ import annotations

import os
import sys
import psycopg2


def db_url() -> str:
    return os.getenv("DATABASE_URL", "postgresql:///finam_core")


DDL = """
DROP MATERIALIZED VIEW IF EXISTS warehouse.kg_statistics_v1;
DROP MATERIALIZED VIEW IF EXISTS warehouse.kg_path_v1;

CREATE OR REPLACE VIEW warehouse.kg_node_v1 AS
SELECT
    'CATALOG'::text AS node_type,
    object_id::text AS node_code,
    object_name::text AS node_name,
    'analytics_asset_catalog_v1'::text AS registry_source,
    health_light::text AS status,
    warehouse_layer::text AS maturity_level,
    source_system::text AS source_of_truth,
    payload::jsonb AS payload
FROM warehouse.analytics_asset_catalog_v1

UNION ALL

SELECT
    'FEATURE'::text AS node_type,
    feature_code::text AS node_code,
    feature_name::text AS node_name,
    'feature_registry_v1'::text AS registry_source,
    status::text AS status,
    maturity_level::text AS maturity_level,
    source_of_truth::text AS source_of_truth,
    payload::jsonb AS payload
FROM warehouse.feature_registry_v1

UNION ALL

SELECT
    'MODEL'::text AS node_type,
    model_code::text AS node_code,
    model_name::text AS node_name,
    'model_registry_v1'::text AS registry_source,
    status::text AS status,
    maturity_level::text AS maturity_level,
    source_of_truth::text AS source_of_truth,
    payload::jsonb AS payload
FROM warehouse.model_registry_v1

UNION ALL

SELECT
    'EXPERIMENT'::text AS node_type,
    experiment_code::text AS node_code,
    experiment_name::text AS node_name,
    'experiment_registry_v1'::text AS registry_source,
    status::text AS status,
    maturity_level::text AS maturity_level,
    source_of_truth::text AS source_of_truth,
    payload::jsonb AS payload
FROM warehouse.experiment_registry_v1;

CREATE OR REPLACE VIEW warehouse.kg_edge_v1 AS
SELECT
    source_domain::text AS source_node_type,
    source_code::text AS source_node_code,
    target_domain::text AS target_node_type,
    target_code::text AS target_node_code,
    relationship_type::text AS relationship_type,
    relationship_strength::numeric AS relationship_strength,
    validation_status::text AS validation_status,
    source_of_truth::text AS source_of_truth,
    evidence_level::text AS evidence_level,
    payload::jsonb AS payload
FROM warehouse.registry_relationship_v1;

CREATE MATERIALIZED VIEW warehouse.kg_path_v1 AS
SELECT
    relationship_type::text AS path_type,
    source_node_type::text AS start_node_type,
    source_node_code::text AS start_node_code,
    target_node_type::text AS end_node_type,
    target_node_code::text AS end_node_code,
    1::int AS path_depth,
    jsonb_build_array(
        jsonb_build_object('node_type', source_node_type, 'node_code', source_node_code),
        jsonb_build_object('node_type', target_node_type, 'node_code', target_node_code)
    ) AS path_nodes,
    jsonb_build_array(relationship_type) AS path_edges,
    validation_status::text AS validation_status,
    source_of_truth::text AS source_of_truth
FROM warehouse.kg_edge_v1
WHERE validation_status='VALIDATED';

CREATE UNIQUE INDEX IF NOT EXISTS idx_kg_path_unique_v1
ON warehouse.kg_path_v1(path_type, start_node_type, start_node_code, end_node_type, end_node_code);

CREATE INDEX IF NOT EXISTS idx_kg_path_start_v1
ON warehouse.kg_path_v1(start_node_type, start_node_code);

CREATE INDEX IF NOT EXISTS idx_kg_path_end_v1
ON warehouse.kg_path_v1(end_node_type, end_node_code);

CREATE MATERIALIZED VIEW warehouse.kg_statistics_v1 AS
WITH nodes AS (
    SELECT count(*)::bigint AS total_nodes,
           count(DISTINCT node_type)::bigint AS node_types
    FROM warehouse.kg_node_v1
),
edges AS (
    SELECT count(*)::bigint AS total_edges,
           count(DISTINCT relationship_type)::bigint AS relationship_types,
           count(*) FILTER (WHERE validation_status <> 'VALIDATED')::bigint AS not_validated_edges
    FROM warehouse.kg_edge_v1
),
isolated AS (
    SELECT count(*)::bigint AS isolated_nodes
    FROM warehouse.kg_node_v1 n
    LEFT JOIN warehouse.kg_edge_v1 e1
      ON e1.source_node_type = n.node_type
     AND e1.source_node_code = n.node_code
    LEFT JOIN warehouse.kg_edge_v1 e2
      ON e2.target_node_type = n.node_type
     AND e2.target_node_code = n.node_code
    WHERE e1.source_node_code IS NULL
      AND e2.target_node_code IS NULL
)
SELECT
    nodes.total_nodes,
    edges.total_edges,
    nodes.node_types,
    edges.relationship_types,
    isolated.isolated_nodes,
    edges.not_validated_edges,
    now() AS refreshed_at
FROM nodes, edges, isolated;

CREATE UNIQUE INDEX IF NOT EXISTS idx_kg_statistics_singleton_v1
ON warehouse.kg_statistics_v1(refreshed_at);
"""


def main() -> int:
    with psycopg2.connect(db_url()) as conn:
        with conn.cursor() as cur:
            cur.execute(DDL)
            conn.commit()

            cur.execute("SELECT count(*)::bigint FROM warehouse.kg_node_v1")
            nodes = int(cur.fetchone()[0])

            cur.execute("SELECT count(*)::bigint FROM warehouse.kg_edge_v1")
            edges = int(cur.fetchone()[0])

            cur.execute("SELECT count(*)::bigint FROM warehouse.kg_path_v1")
            paths = int(cur.fetchone()[0])

            cur.execute("SELECT total_nodes, total_edges, node_types, relationship_types, isolated_nodes, not_validated_edges FROM warehouse.kg_statistics_v1")
            stats = cur.fetchone()

    print("=== KNOWLEDGE_GRAPH_SCHEMA_V1 ===")
    print("слой=VIEW_LAYER")
    print("kg_node=warehouse.kg_node_v1")
    print("kg_edge=warehouse.kg_edge_v1")
    print("kg_path=warehouse.kg_path_v1")
    print("kg_statistics=warehouse.kg_statistics_v1")
    print(f"nodes={nodes}")
    print(f"edges={edges}")
    print(f"paths={paths}")
    print(f"node_types={stats[2]}")
    print(f"relationship_types={stats[3]}")
    print(f"isolated_nodes={stats[4]}")
    print(f"not_validated_edges={stats[5]}")
    print("политика=GRAPH_READ_ONLY_VIEW_LAYER")
    print("source_policy=REGISTRY_AND_RELATIONSHIPS_ARE_SOURCE_OF_TRUTH")
    print("refresh_policy=MATERIALIZED_VIEWS_REFRESHED_BY_MANAGER")
    print("runtime_changed=0")
    print("execution_changed=0")
    print("orders_changed=0")
    print("fills_changed=0")
    print("micro_live_allowed=0")
    print("VERDICT=KNOWLEDGE_GRAPH_SCHEMA_V1_READY")
    return 0


if __name__ == "__main__":
    sys.exit(main())
