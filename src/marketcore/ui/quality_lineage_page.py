from __future__ import annotations

import os
import psycopg2
import psycopg2.extras

from marketcore.ui import Page, Section, render_card, render_page, render_table


def db_url() -> str:
    return os.getenv("DATABASE_URL", "postgresql:///finam_core")


def fetch(sql: str):
    with psycopg2.connect(db_url()) as conn:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute(sql)
            return [dict(r) for r in cur.fetchall()]


def cards_summary() -> str:
    r = fetch("""
        SELECT
          (SELECT count(*) FROM warehouse.normalized_lineage_relationship_type_v1) AS relationship_types,
          (SELECT count(*) FROM warehouse.normalized_lineage_event_v1) AS lineage_events,
          (SELECT count(*) FROM warehouse.normalized_lineage_event_v1 WHERE lineage_valid=true) AS valid_lineage,
          (SELECT count(*) FROM warehouse.normalized_lineage_event_v1 WHERE is_terminal=true) AS terminal_nodes,
          (SELECT count(*) FROM warehouse.normalized_data_quality_event_v1) AS quality_events,
          (SELECT count(*) FROM warehouse.normalized_data_quality_event_v1 WHERE resolved=false) AS unresolved_quality
    """)[0]

    return "".join([
        render_card("Relationship Types", r["relationship_types"]),
        render_card("Lineage Events", r["lineage_events"]),
        render_card("Valid Lineage", r["valid_lineage"]),
        render_card("Terminal Nodes", r["terminal_nodes"]),
        render_card("Quality Events", r["quality_events"]),
        render_card("Unresolved Quality", r["unresolved_quality"]),
    ])


def relationships() -> str:
    rows = fetch("""
        SELECT entity_code, entity_name, relationship_scope, status
        FROM warehouse.normalized_lineage_relationship_type_v1
        ORDER BY relationship_scope, entity_code
        LIMIT 100
    """)
    return render_table(rows)


def graph() -> str:
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
          is_terminal
        FROM warehouse.normalized_lineage_event_v1
        ORDER BY lineage_event_id DESC
        LIMIT 100
    """)
    return render_table(rows)


def health() -> str:
    rows = fetch("""
        SELECT
          count(*) AS total,
          count(*) FILTER (WHERE source_entity_uuid = target_entity_uuid) AS self_edges,
          count(*) FILTER (WHERE confidence < 0 OR confidence > 100) AS bad_confidence,
          count(*) FILTER (WHERE explainability_score < 0 OR explainability_score > 100) AS bad_explainability,
          count(*) FILTER (WHERE lineage_valid=false) AS invalid_lineage,
          count(*) FILTER (WHERE graph_node_uuid IS NULL) AS missing_graph_node
        FROM warehouse.normalized_lineage_event_v1
    """)
    return render_table(rows)


def quality() -> str:
    rows = fetch("""
        SELECT
          r.entity_code AS reason,
          r.quality_dimension,
          r.severity_default,
          r.blocks_research_default,
          r.blocks_ai_default,
          r.blocks_runtime_default,
          r.recommendation_default
        FROM warehouse.normalized_quality_reason_v1 r
        ORDER BY r.quality_dimension, r.entity_code
    """)
    return render_table(rows)


def render_quality_lineage_page() -> str:
    page = Page(
        page_id="quality_lineage",
        title="Quality & Lineage",
        route="/knowledge/lineage",
        group="Knowledge",
        sections=(
            Section("summary", "Summary", cards_summary),
            Section("relationships", "Relationships", relationships),
            Section("graph", "Graph", graph),
            Section("health", "Health", health),
            Section("quality", "Quality", quality),
        ),
        read_only=True,
    )
    return render_page(page)
