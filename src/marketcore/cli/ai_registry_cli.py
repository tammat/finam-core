from __future__ import annotations

import os
import sys
import psycopg2
import psycopg2.extras

from marketcore.registry.cli import flat_print, flat_print_rows
from marketcore.registry.sql import registry_list_sql, registry_search_sql


def db_url() -> str:
    return os.getenv("DATABASE_URL", "postgresql:///finam_core")


def fetch(sql: str, params: tuple = ()) -> list[dict]:
    with psycopg2.connect(db_url()) as conn:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute(sql, params)
            return [dict(r) for r in cur.fetchall()]


def cmd_ai_summary(args) -> int:
    rows = fetch("""
        SELECT ai_type, count(*)::int AS total
        FROM warehouse.ai_registry_v1
        GROUP BY ai_type
        ORDER BY ai_type
    """)
    total = fetch("SELECT count(*)::int AS total FROM warehouse.ai_registry_v1")[0]["total"]

    print("AI_REGISTRY_SUMMARY")
    print(f"total={total}")
    for row in rows:
        print(f"{row['ai_type']}={row['total']}")
    return 0


def cmd_ai_list(args) -> int:
    rows = fetch(registry_list_sql(
        "warehouse.ai_registry_v1",
        ("ai_code", "ai_name", "ai_type", "status", "maturity_level"),
        "ai_code",
        100,
    ))
    flat_print_rows(rows)
    return 0


def cmd_ai_search(args) -> int:
    pattern = f"%{args.query}%"
    rows = fetch(
        registry_search_sql(
            "warehouse.ai_registry_v1",
            ("ai_code", "ai_name", "ai_type", "status", "maturity_level", "description"),
            ("ai_code", "ai_name", "description"),
            "ai_code",
            100,
        ),
        (pattern, pattern, pattern),
    )
    flat_print_rows(rows)
    return 0


def cmd_ai_health(args) -> int:
    row = fetch("""
        SELECT
            (SELECT count(*)::int FROM warehouse.ai_registry_v1) AS total,
            (SELECT count(*)::int FROM warehouse.ai_registry_v1 WHERE approved_for_live=true) AS unsafe_live_rows,
            (SELECT count(*)::int FROM warehouse.ai_registry_v1 WHERE execution_policy='AI_RECOMMENDS_ONLY_NO_DIRECT_EXECUTION') AS execution_policy_valid,
            (SELECT count(*)::int FROM warehouse.ai_registry_v1 WHERE market_knowledge_policy='AI_REGISTRY_STORES_AI_KNOWLEDGE_ONLY') AS market_policy_valid,
            (SELECT count(*)::int FROM warehouse.ai_registry_v1 WHERE graph_required=true) AS graph_required_valid,
            (SELECT count(*)::int FROM warehouse.ai_registry_v1 WHERE payload->>'registry_framework_version'='V1') AS framework_version_valid,
            (SELECT count(*)::int FROM warehouse.ai_registry_v1 WHERE payload->>'domain_types_version'='V1') AS domain_types_version_valid,
            (SELECT count(*)::int FROM warehouse.ai_registry_v1
              WHERE payload ? 'feature_code'
                 OR payload ? 'model_code'
                 OR payload ? 'experiment_code'
                 OR payload ? 'dataset_code'
                 OR payload::text ILIKE '%%feature_code%%'
                 OR payload::text ILIKE '%%model_code%%'
                 OR payload::text ILIKE '%%experiment_code%%'
                 OR payload::text ILIKE '%%dataset_code%%') AS forbidden_market_fields
    """)[0]
    flat_print(row)
    return 0


def register_ai_commands(sub) -> None:
    ai = sub.add_parser("ai")
    ai_sub = ai.add_subparsers(dest="cmd", required=True)

    p = ai_sub.add_parser("summary")
    p.set_defaults(func=cmd_ai_summary)

    p = ai_sub.add_parser("list")
    p.set_defaults(func=cmd_ai_list)

    p = ai_sub.add_parser("search")
    p.add_argument("query")
    p.set_defaults(func=cmd_ai_search)

    p = ai_sub.add_parser("health")
    p.set_defaults(func=cmd_ai_health)
