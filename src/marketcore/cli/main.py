#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
import sys

import psycopg2
import psycopg2.extras


def db_url() -> str:
    return os.getenv("DATABASE_URL", "postgresql:///finam_core")


def fetch(sql: str, params=None):
    with psycopg2.connect(db_url()) as conn:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute(sql, params or ())
            return cur.fetchall()


def emit(data, as_json: bool):
    if as_json:
        print(json.dumps(data, ensure_ascii=False, default=str, indent=2))
    else:
        if isinstance(data, list):
            for row in data:
                print(" | ".join(f"{k}={v}" for k, v in row.items()))
        else:
            for k, v in data.items():
                print(f"{k}={v}")


def cmd_summary(args):
    rows = fetch("""
        SELECT
          count(*) AS objects,
          count(DISTINCT domain) AS domains,
          count(*) FILTER (WHERE payload->>'discovery_source'='PostgresDiscovery') AS postgres,
          count(*) FILTER (WHERE payload->>'discovery_source'='PythonDiscovery') AS python,
          count(*) FILTER (WHERE payload->>'discovery_source'='BashDiscovery') AS bash,
          count(*) FILTER (WHERE health_light='GREEN') AS green
        FROM warehouse.analytics_asset_catalog_v1
    """)
    r = dict(rows[0])
    r["health_pct"] = round((int(r["green"]) / int(r["objects"]) * 100), 2) if int(r["objects"]) else 0
    emit(r, args.json)


def cmd_list(args):
    rows = fetch("""
        SELECT object_id, domain, category, warehouse_layer, health_light
        FROM warehouse.analytics_asset_catalog_v1
        ORDER BY domain, object_id
        LIMIT %s
    """, (args.limit,))
    emit([dict(r) for r in rows], args.json)


def cmd_search(args):
    term = f"%{args.term}%"
    rows = fetch("""
        SELECT object_id, domain, category, warehouse_layer, health_light
        FROM warehouse.analytics_asset_catalog_v1
        WHERE object_id ILIKE %s OR object_name ILIKE %s
        ORDER BY object_id
        LIMIT %s
    """, (term, term, args.limit))
    emit([dict(r) for r in rows], args.json)


def cmd_object(args):
    term = f"%{args.term}%"
    rows = fetch("""
        SELECT object_id, object_name, domain, category, warehouse_layer,
               source_system, source_type, rows_count, health_light,
               validation_status, verification_status, payload
        FROM warehouse.analytics_asset_catalog_v1
        WHERE object_id ILIKE %s OR object_name ILIKE %s
        ORDER BY object_id
        LIMIT 5
    """, (term, term))
    emit([dict(r) for r in rows], args.json)


def cmd_layer(args):
    rows = fetch("""
        SELECT object_id, domain, category, warehouse_layer, health_light
        FROM warehouse.analytics_asset_catalog_v1
        WHERE warehouse_layer=%s
        ORDER BY object_id
    """, (args.layer,))
    emit([dict(r) for r in rows], args.json)


def cmd_source(args):
    rows = fetch("""
        SELECT object_id, domain, category, warehouse_layer, health_light
        FROM warehouse.analytics_asset_catalog_v1
        WHERE payload->>'discovery_source'=%s
        ORDER BY object_id
    """, (args.source,))
    emit([dict(r) for r in rows], args.json)


def cmd_health(args):
    rows = fetch("""
        SELECT
          count(*) AS total,
          count(*) FILTER (WHERE coalesce(object_id,'')='') AS missing_object_id,
          count(*) FILTER (WHERE coalesce(domain,'')='') AS missing_domain,
          count(*) FILTER (WHERE coalesce(category,'')='') AS missing_category,
          count(*) FILTER (WHERE health_light='GREEN') AS green,
          count(*) FILTER (WHERE health_light <> 'GREEN') AS not_green
        FROM warehouse.analytics_asset_catalog_v1
    """)
    emit(dict(rows[0]), args.json)



def cmd_coverage(args):
    rows = fetch("""
        WITH base AS (
            SELECT
              domain,
              count(*) AS total,
              count(*) FILTER (WHERE coalesce(object_id,'') <> '') AS has_object_id,
              count(*) FILTER (WHERE coalesce(source_system,'') <> '') AS has_source_system,
              count(*) FILTER (WHERE coalesce(payload->>'discovery_source','') <> '') AS has_discovery_source,
              count(*) FILTER (WHERE coalesce(warehouse_layer,'') <> '') AS has_layer,
              count(*) FILTER (WHERE health_light='GREEN') AS green
            FROM warehouse.analytics_asset_catalog_v1
            GROUP BY domain
        )
        SELECT
          domain,
          total,
          round((has_object_id::numeric / nullif(total,0)) * 100, 2) AS object_id_coverage_pct,
          round((has_source_system::numeric / nullif(total,0)) * 100, 2) AS source_system_coverage_pct,
          round((has_discovery_source::numeric / nullif(total,0)) * 100, 2) AS discovery_coverage_pct,
          round((has_layer::numeric / nullif(total,0)) * 100, 2) AS layer_coverage_pct,
          round((green::numeric / nullif(total,0)) * 100, 2) AS health_coverage_pct
        FROM base
        ORDER BY domain
    """)
    emit([dict(r) for r in rows], args.json)


def cmd_stats(args):
    rows = fetch("""
        SELECT 'domain' AS stat_type, domain AS key, count(*) AS cnt
        FROM warehouse.analytics_asset_catalog_v1
        GROUP BY domain
        UNION ALL
        SELECT 'layer' AS stat_type, warehouse_layer AS key, count(*) AS cnt
        FROM warehouse.analytics_asset_catalog_v1
        GROUP BY warehouse_layer
        UNION ALL
        SELECT 'source' AS stat_type, payload->>'discovery_source' AS key, count(*) AS cnt
        FROM warehouse.analytics_asset_catalog_v1
        GROUP BY payload->>'discovery_source'
        ORDER BY stat_type, key
    """)
    emit([dict(r) for r in rows], args.json)



def cmd_feature_summary(args):
    rows = fetch("""
        SELECT
          count(*) AS total,
          count(*) FILTER (WHERE status='DISCOVERED') AS discovered,
          count(*) FILTER (WHERE maturity_level='RESEARCH') AS research,
          count(*) FILTER (WHERE approved_for_live=true) AS live_approved
        FROM warehouse.feature_registry_v1
    """)
    emit(dict(rows[0]), args.json)


def cmd_feature_list(args):
    rows = fetch("""
        SELECT feature_code, feature_name, feature_class, status, maturity_level, validation_status
        FROM warehouse.feature_registry_v1
        ORDER BY feature_code
        LIMIT %s
    """, (args.limit,))
    emit([dict(r) for r in rows], args.json)


def cmd_feature_search(args):
    term = f"%{args.term}%"
    rows = fetch("""
        SELECT feature_code, feature_name, feature_class, status, maturity_level, validation_status
        FROM warehouse.feature_registry_v1
        WHERE feature_code ILIKE %s OR feature_name ILIKE %s OR feature_class ILIKE %s
        ORDER BY feature_code
        LIMIT %s
    """, (term, term, term, args.limit))
    emit([dict(r) for r in rows], args.json)


def cmd_feature_health(args):
    rows = fetch("""
        SELECT
          count(*) AS total,
          count(*) FILTER (WHERE coalesce(feature_code,'')='') AS missing_feature_code,
          count(*) FILTER (WHERE coalesce(status,'')='') AS missing_status,
          count(*) FILTER (WHERE approved_for_live=true OR approved_for_paper=true OR approved_for_shadow=true) AS unsafe_approvals
        FROM warehouse.feature_registry_v1
    """)
    emit(dict(rows[0]), args.json)



def cmd_model_summary(args):
    rows = fetch("""
        SELECT
          count(*) AS total,
          count(*) FILTER (WHERE status='DISCOVERED') AS discovered,
          count(*) FILTER (WHERE maturity_level='RESEARCH') AS research,
          count(*) FILTER (WHERE approved_for_live=true) AS live_approved
        FROM warehouse.model_registry_v1
    """)
    emit(dict(rows[0]), args.json)


def cmd_model_list(args):
    rows = fetch("""
        SELECT model_code, model_name, model_class, model_family, status, maturity_level, validation_status
        FROM warehouse.model_registry_v1
        ORDER BY model_code
        LIMIT %s
    """, (args.limit,))
    emit([dict(r) for r in rows], args.json)


def cmd_model_search(args):
    term = f"%{args.term}%"
    rows = fetch("""
        SELECT model_code, model_name, model_class, model_family, status, maturity_level, validation_status
        FROM warehouse.model_registry_v1
        WHERE model_code ILIKE %s OR model_name ILIKE %s OR model_class ILIKE %s OR model_family ILIKE %s
        ORDER BY model_code
        LIMIT %s
    """, (term, term, term, term, args.limit))
    emit([dict(r) for r in rows], args.json)


def cmd_model_health(args):
    rows = fetch("""
        SELECT
          count(*) AS total,
          count(*) FILTER (WHERE coalesce(model_code,'')='') AS missing_model_code,
          count(*) FILTER (WHERE coalesce(status,'')='') AS missing_status,
          count(*) FILTER (WHERE approved_for_live=true OR approved_for_paper=true OR approved_for_shadow=true) AS unsafe_approvals
        FROM warehouse.model_registry_v1
    """)
    emit(dict(rows[0]), args.json)



def cmd_experiment_summary(args):
    rows = fetch("""
        SELECT
          count(*) AS total,
          count(*) FILTER (WHERE status='REGISTERED') AS registered,
          count(*) FILTER (WHERE maturity_level='RESEARCH') AS research,
          count(*) FILTER (WHERE approved_for_live=true) AS live_approved
        FROM warehouse.experiment_registry_v1
    """)
    emit(dict(rows[0]), args.json)


def cmd_experiment_list(args):
    rows = fetch("""
        SELECT experiment_code, experiment_name, symbol, timeframe,
               strategy_code, status, maturity_level, decision
        FROM warehouse.experiment_registry_v1
        ORDER BY updated_at DESC, experiment_code
        LIMIT %s
    """, (args.limit,))
    emit([dict(r) for r in rows], args.json)


def cmd_experiment_search(args):
    term = f"%{args.term}%"
    rows = fetch("""
        SELECT experiment_code, experiment_name, symbol, timeframe,
               strategy_code, status, maturity_level, decision
        FROM warehouse.experiment_registry_v1
        WHERE experiment_code ILIKE %s
           OR experiment_name ILIKE %s
           OR symbol ILIKE %s
           OR strategy_code ILIKE %s
           OR decision ILIKE %s
        ORDER BY updated_at DESC, experiment_code
        LIMIT %s
    """, (term, term, term, term, term, args.limit))
    emit([dict(r) for r in rows], args.json)


def cmd_experiment_health(args):
    rows = fetch("""
        SELECT
          count(*) AS total,
          count(*) FILTER (WHERE coalesce(experiment_code,'')='') AS missing_experiment_code,
          count(*) FILTER (WHERE coalesce(status,'')='') AS missing_status,
          count(*) FILTER (WHERE approved_for_live=true OR approved_for_paper=true OR approved_for_shadow=true) AS unsafe_approvals
        FROM warehouse.experiment_registry_v1
    """)
    emit(dict(rows[0]), args.json)



def cmd_relationship_summary(args):
    rows = fetch("""
        SELECT relationship_type, count(*) AS total
        FROM warehouse.registry_relationship_v1
        GROUP BY relationship_type
        ORDER BY relationship_type
    """)
    emit([dict(r) for r in rows], args.json)


def cmd_relationship_list(args):
    rows = fetch("""
        SELECT source_domain, source_code, target_domain, target_code,
               relationship_type, validation_status
        FROM warehouse.registry_relationship_v1
        ORDER BY relationship_type, source_code
        LIMIT %s
    """, (args.limit,))
    emit([dict(r) for r in rows], args.json)


def cmd_relationship_health(args):
    rows = fetch("""
        SELECT
          count(*) AS total,
          count(*) FILTER (WHERE coalesce(source_code,'')='') AS missing_source_code,
          count(*) FILTER (WHERE coalesce(target_code,'')='') AS missing_target_code,
          count(*) FILTER (WHERE validation_status <> 'VALIDATED') AS not_validated
        FROM warehouse.registry_relationship_v1
    """)
    emit(dict(rows[0]), args.json)



def cmd_graph_summary(args):
    rows = fetch("""
        SELECT total_nodes, total_edges, node_types, relationship_types,
               isolated_nodes, not_validated_edges, refreshed_at
        FROM warehouse.kg_statistics_v1
    """)
    emit(dict(rows[0]), args.json)


def cmd_graph_nodes(args):
    rows = fetch("""
        SELECT node_type, count(*) AS total
        FROM warehouse.kg_node_v1
        GROUP BY node_type
        ORDER BY node_type
    """)
    emit([dict(r) for r in rows], args.json)


def cmd_graph_edges(args):
    rows = fetch("""
        SELECT relationship_type, count(*) AS total
        FROM warehouse.kg_edge_v1
        GROUP BY relationship_type
        ORDER BY relationship_type
    """)
    emit([dict(r) for r in rows], args.json)


def cmd_graph_paths(args):
    rows = fetch("""
        SELECT path_type, count(*) AS total
        FROM warehouse.kg_path_v1
        GROUP BY path_type
        ORDER BY path_type
    """)
    emit([dict(r) for r in rows], args.json)


def cmd_graph_isolated(args):
    rows = fetch("""
        SELECT node_type, count(*) AS total
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
    emit([dict(r) for r in rows], args.json)


def cmd_graph_health(args):
    rows = fetch("""
        SELECT
          (SELECT count(*) FROM warehouse.kg_node_v1) AS nodes,
          (SELECT count(*) FROM warehouse.kg_edge_v1) AS edges,
          (SELECT count(*) FROM warehouse.kg_path_v1) AS paths,
          (SELECT count(*) FROM warehouse.kg_edge_v1 WHERE validation_status <> 'VALIDATED') AS not_validated_edges,
          (SELECT count(*) FROM warehouse.kg_path_v1 WHERE validation_status <> 'VALIDATED') AS not_validated_paths
    """)
    emit(dict(rows[0]), args.json)


def main() -> int:
    parser = argparse.ArgumentParser(prog="marketcore")
    sub = parser.add_subparsers(dest="area", required=True)






    graph = sub.add_parser("graph")
    graph_sub = graph.add_subparsers(dest="cmd", required=True)

    p = graph_sub.add_parser("summary")
    p.add_argument("--json", action="store_true")
    p.set_defaults(func=cmd_graph_summary)

    p = graph_sub.add_parser("nodes")
    p.add_argument("--json", action="store_true")
    p.set_defaults(func=cmd_graph_nodes)

    p = graph_sub.add_parser("edges")
    p.add_argument("--json", action="store_true")
    p.set_defaults(func=cmd_graph_edges)

    p = graph_sub.add_parser("paths")
    p.add_argument("--json", action="store_true")
    p.set_defaults(func=cmd_graph_paths)

    p = graph_sub.add_parser("isolated")
    p.add_argument("--json", action="store_true")
    p.set_defaults(func=cmd_graph_isolated)

    p = graph_sub.add_parser("health")
    p.add_argument("--json", action="store_true")
    p.set_defaults(func=cmd_graph_health)

    relationship = sub.add_parser("relationship")
    relationship_sub = relationship.add_subparsers(dest="cmd", required=True)

    p = relationship_sub.add_parser("summary")
    p.add_argument("--json", action="store_true")
    p.set_defaults(func=cmd_relationship_summary)

    p = relationship_sub.add_parser("list")
    p.add_argument("--limit", type=int, default=50)
    p.add_argument("--json", action="store_true")
    p.set_defaults(func=cmd_relationship_list)

    p = relationship_sub.add_parser("health")
    p.add_argument("--json", action="store_true")
    p.set_defaults(func=cmd_relationship_health)

    experiment = sub.add_parser("experiment")
    experiment_sub = experiment.add_subparsers(dest="cmd", required=True)

    p = experiment_sub.add_parser("summary")
    p.add_argument("--json", action="store_true")
    p.set_defaults(func=cmd_experiment_summary)

    p = experiment_sub.add_parser("list")
    p.add_argument("--limit", type=int, default=50)
    p.add_argument("--json", action="store_true")
    p.set_defaults(func=cmd_experiment_list)

    p = experiment_sub.add_parser("search")
    p.add_argument("term")
    p.add_argument("--limit", type=int, default=50)
    p.add_argument("--json", action="store_true")
    p.set_defaults(func=cmd_experiment_search)

    p = experiment_sub.add_parser("health")
    p.add_argument("--json", action="store_true")
    p.set_defaults(func=cmd_experiment_health)

    model = sub.add_parser("model")
    model_sub = model.add_subparsers(dest="cmd", required=True)

    p = model_sub.add_parser("summary")
    p.add_argument("--json", action="store_true")
    p.set_defaults(func=cmd_model_summary)

    p = model_sub.add_parser("list")
    p.add_argument("--limit", type=int, default=50)
    p.add_argument("--json", action="store_true")
    p.set_defaults(func=cmd_model_list)

    p = model_sub.add_parser("search")
    p.add_argument("term")
    p.add_argument("--limit", type=int, default=50)
    p.add_argument("--json", action="store_true")
    p.set_defaults(func=cmd_model_search)

    p = model_sub.add_parser("health")
    p.add_argument("--json", action="store_true")
    p.set_defaults(func=cmd_model_health)

    feature = sub.add_parser("feature")
    feature_sub = feature.add_subparsers(dest="cmd", required=True)

    p = feature_sub.add_parser("summary")
    p.add_argument("--json", action="store_true")
    p.set_defaults(func=cmd_feature_summary)

    p = feature_sub.add_parser("list")
    p.add_argument("--limit", type=int, default=50)
    p.add_argument("--json", action="store_true")
    p.set_defaults(func=cmd_feature_list)

    p = feature_sub.add_parser("search")
    p.add_argument("term")
    p.add_argument("--limit", type=int, default=50)
    p.add_argument("--json", action="store_true")
    p.set_defaults(func=cmd_feature_search)

    p = feature_sub.add_parser("health")
    p.add_argument("--json", action="store_true")
    p.set_defaults(func=cmd_feature_health)

    catalog = sub.add_parser("catalog")
    catalog_sub = catalog.add_subparsers(dest="cmd", required=True)

    p = catalog_sub.add_parser("summary")
    p.add_argument("--json", action="store_true")
    p.set_defaults(func=cmd_summary)

    p = catalog_sub.add_parser("list")
    p.add_argument("--limit", type=int, default=50)
    p.add_argument("--json", action="store_true")
    p.set_defaults(func=cmd_list)

    p = catalog_sub.add_parser("search")
    p.add_argument("term")
    p.add_argument("--limit", type=int, default=50)
    p.add_argument("--json", action="store_true")
    p.set_defaults(func=cmd_search)

    p = catalog_sub.add_parser("object")
    p.add_argument("term")
    p.add_argument("--json", action="store_true")
    p.set_defaults(func=cmd_object)

    p = catalog_sub.add_parser("layer")
    p.add_argument("layer")
    p.add_argument("--json", action="store_true")
    p.set_defaults(func=cmd_layer)

    p = catalog_sub.add_parser("source")
    p.add_argument("source")
    p.add_argument("--json", action="store_true")
    p.set_defaults(func=cmd_source)

    p = catalog_sub.add_parser("health")
    p.add_argument("--json", action="store_true")
    p.set_defaults(func=cmd_health)


    p = catalog_sub.add_parser("coverage")
    p.add_argument("--json", action="store_true")
    p.set_defaults(func=cmd_coverage)

    p = catalog_sub.add_parser("stats")
    p.add_argument("--json", action="store_true")
    p.set_defaults(func=cmd_stats)

    args = parser.parse_args()
    args.func(args)

    print("runtime_changed=0")
    print("execution_changed=0")
    print("orders_changed=0")
    print("fills_changed=0")
    print("micro_live_allowed=0")
    return 0


if __name__ == "__main__":
    sys.exit(main())
