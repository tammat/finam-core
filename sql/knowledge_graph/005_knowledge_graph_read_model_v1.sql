BEGIN;

CREATE OR REPLACE VIEW knowledge_graph.v_api_kg_entity_summary_v1 AS
SELECT
    n.domain,
    n.entity_type,
    n.node_id,
    n.source_table,
    n.source_pk,
    n.external_id,
    n.symbol,
    n.strategy,
    n.timeframe,
    n.trade_source,
    n.confidence,
    n.ontology_version,
    n.created_at,
    n.updated_at,
    COALESCE(l_ru.label, n.entity_type) AS label_ru,
    COALESCE(l_en.label, n.entity_type) AS label_en,
    n.payload
FROM knowledge_graph.nodes n
LEFT JOIN knowledge_graph.i18n_labels l_ru
  ON l_ru.object_type='entity_type'
 AND l_ru.object_key=n.entity_type
 AND l_ru.locale='ru'
 AND l_ru.ontology_version=n.ontology_version
LEFT JOIN knowledge_graph.i18n_labels l_en
  ON l_en.object_type='entity_type'
 AND l_en.object_key=n.entity_type
 AND l_en.locale='en'
 AND l_en.ontology_version=n.ontology_version;

CREATE OR REPLACE VIEW knowledge_graph.v_api_kg_relation_summary_v1 AS
SELECT
    e.domain,
    e.edge_id,
    e.edge_type,
    e.from_node_id,
    src.entity_type AS from_entity_type,
    src.source_pk AS from_source_pk,
    src.symbol AS from_symbol,
    e.to_node_id,
    dst.entity_type AS to_entity_type,
    dst.source_pk AS to_source_pk,
    dst.symbol AS to_symbol,
    e.confidence,
    e.ontology_version,
    COALESCE(l_ru.label, e.edge_type) AS label_ru,
    COALESCE(l_en.label, e.edge_type) AS label_en,
    e.payload,
    e.created_at
FROM knowledge_graph.edges e
JOIN knowledge_graph.nodes src ON src.node_id=e.from_node_id
JOIN knowledge_graph.nodes dst ON dst.node_id=e.to_node_id
LEFT JOIN knowledge_graph.i18n_labels l_ru
  ON l_ru.object_type='edge_type'
 AND l_ru.object_key=e.edge_type
 AND l_ru.locale='ru'
 AND l_ru.ontology_version=e.ontology_version
LEFT JOIN knowledge_graph.i18n_labels l_en
  ON l_en.object_type='edge_type'
 AND l_en.object_key=e.edge_type
 AND l_en.locale='en'
 AND l_en.ontology_version=e.ontology_version;

CREATE OR REPLACE VIEW knowledge_graph.v_api_kg_statistics_v1 AS
WITH node_stats AS (
    SELECT
        domain,
        count(*) AS nodes,
        count(DISTINCT entity_type) AS entity_types,
        max(updated_at) AS last_node_update
    FROM knowledge_graph.nodes
    GROUP BY domain
),
edge_stats AS (
    SELECT
        domain,
        count(*) AS edges,
        count(DISTINCT edge_type) AS edge_types
    FROM knowledge_graph.edges
    GROUP BY domain
)
SELECT
    n.domain,
    n.nodes,
    COALESCE(e.edges, 0) AS edges,
    n.entity_types,
    COALESCE(e.edge_types, 0) AS edge_types,
    n.last_node_update
FROM node_stats n
LEFT JOIN edge_stats e ON e.domain=n.domain;

CREATE OR REPLACE VIEW knowledge_graph.v_api_kg_validation_latest_v1 AS
SELECT DISTINCT ON (domain)
    run_id,
    domain,
    status,
    total_findings,
    started_at,
    finished_at,
    payload
FROM knowledge_graph.validation_runs
ORDER BY domain, run_id DESC;

CREATE OR REPLACE VIEW knowledge_graph.v_api_kg_semantic_search_v1 AS
SELECT
    locale,
    normalized_term,
    raw_term,
    object_type,
    object_key,
    match_type,
    confidence,
    source,
    ontology_version
FROM knowledge_graph.v_semantic_lookup_v1;

GRANT SELECT ON ALL TABLES IN SCHEMA knowledge_graph TO alex;

COMMIT;

SELECT 'KNOWLEDGE_GRAPH_READ_MODEL_V1_READY' AS verdict;
