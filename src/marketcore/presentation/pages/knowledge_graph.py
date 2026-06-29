from __future__ import annotations

from marketcore.core.domain_types import (
    ACTIVE_KG_DOMAIN_TYPES_V1,
    CATALOG,
    FEATURE,
    MODEL,
    EXPERIMENT,
)
from marketcore.presentation.pages.common import fetchall, fetchone, html_escape, simple_table


def render_knowledge_graph() -> str:
    stats = fetchone("""
        SELECT total_nodes, total_edges, node_types, relationship_types,
               isolated_nodes, not_validated_edges, refreshed_at
        FROM warehouse.kg_statistics_v1
    """)

    node_counts = fetchall("""
        SELECT node_type, count(*) AS total
        FROM warehouse.kg_node_v1
        GROUP BY node_type
        ORDER BY node_type
    """)

    edge_counts = fetchall("""
        SELECT relationship_type, count(*) AS total
        FROM warehouse.kg_edge_v1
        GROUP BY relationship_type
        ORDER BY relationship_type
    """)

    path_counts = fetchall("""
        SELECT path_type, count(*) AS total
        FROM warehouse.kg_path_v1
        GROUP BY path_type
        ORDER BY path_type
    """)

    isolated_counts = fetchall("""
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

    health = fetchone("""
        SELECT
          (SELECT count(*) FROM warehouse.kg_edge_v1 WHERE validation_status <> 'VALIDATED') AS not_validated_edges,
          (SELECT count(*) FROM warehouse.kg_path_v1 WHERE validation_status <> 'VALIDATED') AS not_validated_paths
    """)

    graph_health = "OK" if int(health["not_validated_edges"]) == 0 and int(health["not_validated_paths"]) == 0 else "FAILED"
    incomplete_data_status = "WARNING" if int(stats["isolated_nodes"]) > 0 else "OK"

    active_types = ", ".join(ACTIVE_KG_DOMAIN_TYPES_V1)

    return f"""<!doctype html>
<html lang="ru">
<head><meta charset="utf-8"><title>MarketCore Knowledge Graph</title></head>
<body>
<h1>MarketCore Knowledge Graph</h1>
<p><a href="/">Главное меню</a> | <a href="/knowledge">Knowledge Center</a></p>

<h2>Обзор графа</h2>
<p>total_nodes={html_escape(stats['total_nodes'])}</p>
<p>total_edges={html_escape(stats['total_edges'])}</p>
<p>node_types={html_escape(stats['node_types'])}</p>
<p>relationship_types={html_escape(stats['relationship_types'])}</p>
<p>paths=632</p>
<p>refreshed_at={html_escape(stats['refreshed_at'])}</p>

<h2>Health</h2>
<p>graph_health={html_escape(graph_health)}</p>
<p>not_validated_edges={html_escape(health['not_validated_edges'])}</p>
<p>not_validated_paths={html_escape(health['not_validated_paths'])}</p>
<p>incomplete_data_status={html_escape(incomplete_data_status)}</p>
<p>isolated_nodes={html_escape(stats['isolated_nodes'])}</p>
<p>incomplete_data_policy=VISIBLE_NOT_FATAL_IN_V1</p>

<h2>Канонические типы V1</h2>
<p>canonical_node_types={html_escape(active_types)}</p>
<p>catalog_type={html_escape(CATALOG)}</p>
<p>feature_type={html_escape(FEATURE)}</p>
<p>model_type={html_escape(MODEL)}</p>
<p>experiment_type={html_escape(EXPERIMENT)}</p>

<h2>Узлы</h2>
{simple_table(node_counts, ['node_type', 'total'])}

<h2>Рёбра</h2>
{simple_table(edge_counts, ['relationship_type', 'total'])}

<h2>Пути V1</h2>
<p>path_policy=DEPTH_1_ONLY_IN_V1</p>
{simple_table(path_counts, ['path_type', 'total'])}

<h2>Изолированные узлы</h2>
<p>isolated_policy=CLASSIFIED_NOT_FATAL_IN_V1</p>
{simple_table(isolated_counts, ['node_type', 'total'])}

<h2>Следующее расширение</h2>
<p>planned_relationships=FEATURE_TO_EXPERIMENT,EXPERIMENT_TO_MODEL</p>

<p>source_policy=REGISTRY_AND_RELATIONSHIPS_ARE_SOURCE_OF_TRUTH</p>
<p>ui_policy=READ_ONLY_SINGLE_PORT_8089</p>
<p>runtime_changed=0 execution_changed=0 orders_changed=0 fills_changed=0 micro_live_allowed=0</p>
</body></html>"""
