BEGIN;

CREATE SCHEMA IF NOT EXISTS knowledge_graph;

CREATE TABLE IF NOT EXISTS knowledge_graph.nodes (

    node_id            BIGSERIAL PRIMARY KEY,

    domain             TEXT NOT NULL,
    entity_type        TEXT NOT NULL,

    source_table       TEXT NOT NULL,
    source_pk          TEXT NOT NULL,
    source_path        TEXT,

    external_id        TEXT,

    symbol             TEXT,
    strategy           TEXT,
    timeframe          TEXT,
    trade_source       TEXT,

    confidence         TEXT NOT NULL DEFAULT 'FULL',

    payload            JSONB NOT NULL DEFAULT '{}'::jsonb,

    created_at         TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at         TIMESTAMPTZ NOT NULL DEFAULT now(),

    ontology_version   TEXT NOT NULL,

    UNIQUE(domain, source_table, source_pk, entity_type)

);

CREATE TABLE IF NOT EXISTS knowledge_graph.edges (

    edge_id            BIGSERIAL PRIMARY KEY,

    domain             TEXT NOT NULL,

    from_node_id       BIGINT NOT NULL
        REFERENCES knowledge_graph.nodes(node_id)
        ON DELETE CASCADE,

    to_node_id         BIGINT NOT NULL
        REFERENCES knowledge_graph.nodes(node_id)
        ON DELETE CASCADE,

    edge_type          TEXT NOT NULL,

    confidence         TEXT NOT NULL DEFAULT 'FULL',

    source_table       TEXT,
    source_pk          TEXT,

    payload            JSONB NOT NULL DEFAULT '{}'::jsonb,

    created_at         TIMESTAMPTZ NOT NULL DEFAULT now(),

    ontology_version   TEXT NOT NULL,

    UNIQUE(from_node_id,to_node_id,edge_type)

);

CREATE INDEX IF NOT EXISTS idx_kg_nodes_domain
ON knowledge_graph.nodes(domain);

CREATE INDEX IF NOT EXISTS idx_kg_nodes_entity
ON knowledge_graph.nodes(entity_type);

CREATE INDEX IF NOT EXISTS idx_kg_nodes_symbol
ON knowledge_graph.nodes(symbol);

CREATE INDEX IF NOT EXISTS idx_kg_edges_domain
ON knowledge_graph.edges(domain);

CREATE INDEX IF NOT EXISTS idx_kg_edges_type
ON knowledge_graph.edges(edge_type);

GRANT USAGE ON SCHEMA knowledge_graph TO alex;

GRANT
SELECT,INSERT,UPDATE,DELETE
ON ALL TABLES IN SCHEMA knowledge_graph
TO alex;

COMMIT;

GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA knowledge_graph TO alex;
ALTER DEFAULT PRIVILEGES IN SCHEMA knowledge_graph
GRANT USAGE, SELECT ON SEQUENCES TO alex;

CREATE INDEX IF NOT EXISTS idx_kg_nodes_lookup_v1
ON knowledge_graph.nodes(domain, entity_type, source_pk);

CREATE INDEX IF NOT EXISTS idx_kg_nodes_external_lookup_v1
ON knowledge_graph.nodes(domain, entity_type, external_id);

CREATE INDEX IF NOT EXISTS idx_kg_edges_lookup_v1
ON knowledge_graph.edges(domain, edge_type);
