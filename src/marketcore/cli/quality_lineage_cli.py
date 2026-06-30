from __future__ import annotations

import json
import os

import psycopg2
import psycopg2.extras


def db_url() -> str:
    return os.getenv("DATABASE_URL", "postgresql:///finam_core")


def fetch(sql: str, params=None):
    with psycopg2.connect(db_url()) as conn:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute(sql, params or ())
            return cur.fetchall()


def emit(data, as_json: bool) -> None:
    if as_json:
        print(json.dumps(data, ensure_ascii=False, default=str, indent=2))
        return

    if isinstance(data, list):
        for row in data:
            print(" | ".join(f"{k}={v}" for k, v in row.items()))
    else:
        for k, v in data.items():
            print(f"{k}={v}")


def cmd_lineage_summary(args) -> None:
    rows = fetch("""
        SELECT
            (SELECT count(*) FROM warehouse.normalized_lineage_relationship_type_v1) AS relationship_types,
            (SELECT count(*) FROM warehouse.normalized_lineage_event_v1) AS lineage_events,
            (SELECT count(*) FROM warehouse.normalized_lineage_event_v1 WHERE lineage_valid=true) AS valid_lineage,
            (SELECT count(*) FROM warehouse.normalized_lineage_event_v1 WHERE is_terminal=true) AS terminal_nodes,
            (SELECT count(*) FROM warehouse.normalized_lineage_event_v1 WHERE graph_node_uuid IS NOT NULL) AS graph_links
    """)
    emit(dict(rows[0]), args.json)


def cmd_lineage_relationships(args) -> None:
    rows = fetch("""
        SELECT entity_code, entity_name, relationship_scope, status
        FROM warehouse.normalized_lineage_relationship_type_v1
        ORDER BY relationship_scope, entity_code
        LIMIT %s
    """, (args.limit,))
    emit([dict(r) for r in rows], args.json)


def cmd_lineage_health(args) -> None:
    rows = fetch("""
        SELECT
            count(*) AS total,
            count(*) FILTER (WHERE lineage_uuid IS NULL) AS missing_lineage_uuid,
            count(*) FILTER (WHERE root_entity_uuid IS NULL) AS missing_root_entity_uuid,
            count(*) FILTER (WHERE source_entity_uuid IS NULL) AS missing_source_entity_uuid,
            count(*) FILTER (WHERE target_entity_uuid IS NULL) AS missing_target_entity_uuid,
            count(*) FILTER (WHERE source_entity_uuid = target_entity_uuid) AS self_edges,
            count(*) FILTER (WHERE confidence < 0 OR confidence > 100) AS bad_confidence,
            count(*) FILTER (WHERE explainability_score < 0 OR explainability_score > 100) AS bad_explainability
        FROM warehouse.normalized_lineage_event_v1
    """)
    emit(dict(rows[0]), args.json)


def cmd_lineage_search(args) -> None:
    term = f"%{args.term}%"
    rows = fetch("""
        SELECT
            lineage_uuid,
            root_entity_uuid,
            source_entity_uuid,
            target_entity_uuid,
            lineage_scope,
            lineage_stage,
            lineage_depth,
            lineage_valid,
            is_terminal,
            graph_node_uuid
        FROM warehouse.normalized_lineage_event_v1
        WHERE lineage_uuid::text ILIKE %s
           OR root_entity_uuid::text ILIKE %s
           OR source_entity_uuid::text ILIKE %s
           OR target_entity_uuid::text ILIKE %s
           OR coalesce(path_hash,'') ILIKE %s
        ORDER BY lineage_event_id DESC
        LIMIT %s
    """, (term, term, term, term, term, args.limit))
    emit([dict(r) for r in rows], args.json)


def cmd_quality_summary(args) -> None:
    rows = fetch("""
        SELECT
            (SELECT count(*) FROM warehouse.normalized_quality_reason_v1) AS quality_reasons,
            (SELECT count(*) FROM warehouse.normalized_resolution_method_v1) AS resolution_methods,
            (SELECT count(*) FROM warehouse.normalized_data_quality_event_v1) AS quality_events,
            (SELECT count(*) FROM warehouse.normalized_data_quality_event_v1 WHERE resolved=false) AS unresolved,
            (SELECT count(*) FROM warehouse.normalized_data_quality_event_v1 WHERE blocks_research=true) AS blocks_research,
            (SELECT count(*) FROM warehouse.normalized_data_quality_event_v1 WHERE blocks_ai=true) AS blocks_ai,
            (SELECT count(*) FROM warehouse.normalized_data_quality_event_v1 WHERE blocks_runtime=true) AS blocks_runtime
    """)
    emit(dict(rows[0]), args.json)


def cmd_quality_reasons(args) -> None:
    rows = fetch("""
        SELECT
            entity_code,
            entity_name,
            quality_dimension,
            severity_default,
            blocks_research_default,
            blocks_ai_default,
            blocks_runtime_default,
            recommendation_default,
            status
        FROM warehouse.normalized_quality_reason_v1
        ORDER BY quality_dimension, entity_code
        LIMIT %s
    """, (args.limit,))
    emit([dict(r) for r in rows], args.json)


def cmd_quality_unresolved(args) -> None:
    rows = fetch("""
        SELECT
            q.quality_event_uuid,
            r.entity_code AS reason,
            q.severity_level,
            q.confidence,
            q.affected_event_uuid,
            q.affected_table,
            q.blocks_research,
            q.blocks_ai,
            q.blocks_runtime,
            q.recommendation,
            q.created_at
        FROM warehouse.normalized_data_quality_event_v1 q
        JOIN warehouse.normalized_quality_reason_v1 r ON r.id=q.quality_reason_id
        WHERE q.resolved=false
        ORDER BY q.created_at DESC
        LIMIT %s
    """, (args.limit,))
    emit([dict(r) for r in rows], args.json)


def cmd_quality_blocked(args) -> None:
    rows = fetch("""
        SELECT
            count(*) FILTER (WHERE blocks_research=true AND resolved=false) AS unresolved_blocks_research,
            count(*) FILTER (WHERE blocks_ai=true AND resolved=false) AS unresolved_blocks_ai,
            count(*) FILTER (WHERE blocks_runtime=true AND resolved=false) AS unresolved_blocks_runtime
        FROM warehouse.normalized_data_quality_event_v1
    """)
    emit(dict(rows[0]), args.json)


def register_quality_lineage_commands(sub) -> None:
    lineage = sub.add_parser("lineage")
    lineage_sub = lineage.add_subparsers(dest="cmd", required=True)

    p = lineage_sub.add_parser("summary")
    p.add_argument("--json", action="store_true")
    p.set_defaults(func=cmd_lineage_summary)

    p = lineage_sub.add_parser("relationships")
    p.add_argument("--limit", type=int, default=100)
    p.add_argument("--json", action="store_true")
    p.set_defaults(func=cmd_lineage_relationships)

    p = lineage_sub.add_parser("search")
    p.add_argument("term")
    p.add_argument("--limit", type=int, default=50)
    p.add_argument("--json", action="store_true")
    p.set_defaults(func=cmd_lineage_search)

    p = lineage_sub.add_parser("health")
    p.add_argument("--json", action="store_true")
    p.set_defaults(func=cmd_lineage_health)

    quality = sub.add_parser("quality")
    quality_sub = quality.add_subparsers(dest="cmd", required=True)

    p = quality_sub.add_parser("summary")
    p.add_argument("--json", action="store_true")
    p.set_defaults(func=cmd_quality_summary)

    p = quality_sub.add_parser("reasons")
    p.add_argument("--limit", type=int, default=100)
    p.add_argument("--json", action="store_true")
    p.set_defaults(func=cmd_quality_reasons)

    p = quality_sub.add_parser("unresolved")
    p.add_argument("--limit", type=int, default=50)
    p.add_argument("--json", action="store_true")
    p.set_defaults(func=cmd_quality_unresolved)

    p = quality_sub.add_parser("blocked")
    p.add_argument("--json", action="store_true")
    p.set_defaults(func=cmd_quality_blocked)
