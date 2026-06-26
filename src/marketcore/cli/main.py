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


def main() -> int:
    parser = argparse.ArgumentParser(prog="marketcore")
    sub = parser.add_subparsers(dest="area", required=True)

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
