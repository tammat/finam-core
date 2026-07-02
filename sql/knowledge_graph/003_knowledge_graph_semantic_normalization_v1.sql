BEGIN;

CREATE TABLE IF NOT EXISTS knowledge_graph.semantic_terms (
    term_id BIGSERIAL PRIMARY KEY,
    locale TEXT NOT NULL REFERENCES knowledge_graph.languages(locale),
    raw_term TEXT NOT NULL,
    normalized_term TEXT NOT NULL,
    object_type TEXT NOT NULL,
    object_key TEXT NOT NULL,
    match_type TEXT NOT NULL DEFAULT 'ALIAS',
    ontology_version TEXT NOT NULL,
    confidence NUMERIC(5,4) NOT NULL DEFAULT 1.0,
    source TEXT NOT NULL DEFAULT 'I18N',
    enabled BOOLEAN NOT NULL DEFAULT true,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE(locale, normalized_term, object_type, object_key, ontology_version)
);

CREATE INDEX IF NOT EXISTS idx_kg_semantic_terms_lookup_v1
ON knowledge_graph.semantic_terms(locale, normalized_term);

CREATE INDEX IF NOT EXISTS idx_kg_semantic_terms_object_v1
ON knowledge_graph.semantic_terms(object_type, object_key);

INSERT INTO knowledge_graph.semantic_terms (
    locale, raw_term, normalized_term, object_type, object_key,
    match_type, ontology_version, confidence, source
)
SELECT
    locale,
    label,
    lower(trim(label)),
    object_type,
    object_key,
    'LABEL',
    ontology_version,
    quality_score,
    'I18N_LABEL'
FROM knowledge_graph.i18n_labels
ON CONFLICT DO NOTHING;

INSERT INTO knowledge_graph.semantic_terms (
    locale, raw_term, normalized_term, object_type, object_key,
    match_type, ontology_version, confidence, source
)
SELECT
    locale,
    alias,
    lower(trim(alias)),
    object_type,
    object_key,
    alias_type,
    ontology_version,
    quality_score,
    'I18N_ALIAS'
FROM knowledge_graph.i18n_aliases
ON CONFLICT DO NOTHING;

INSERT INTO knowledge_graph.semantic_terms (
    locale, raw_term, normalized_term, object_type, object_key,
    match_type, ontology_version, confidence, source
)
VALUES
('ru','сделка','сделка','entity_type','ClosedTrade','BUSINESS_TERM','FINAM_CORE_EXPLAINABILITY_KG_ONTOLOGY_V1',0.95,'MANUAL'),
('ru','сделки','сделки','entity_type','ClosedTrade','BUSINESS_TERM','FINAM_CORE_EXPLAINABILITY_KG_ONTOLOGY_V1',0.95,'MANUAL'),
('ru','закрытые сделки','закрытые сделки','entity_type','ClosedTrade','BUSINESS_TERM','FINAM_CORE_EXPLAINABILITY_KG_ONTOLOGY_V1',1.0,'MANUAL'),
('ru','завершенные сделки','завершенные сделки','entity_type','ClosedTrade','BUSINESS_TERM','FINAM_CORE_EXPLAINABILITY_KG_ONTOLOGY_V1',1.0,'MANUAL'),
('ru','исполнение','исполнение','entity_type','Fill','BUSINESS_TERM','FINAM_CORE_EXPLAINABILITY_KG_ONTOLOGY_V1',1.0,'MANUAL'),
('ru','исполнения','исполнения','entity_type','Fill','BUSINESS_TERM','FINAM_CORE_EXPLAINABILITY_KG_ONTOLOGY_V1',1.0,'MANUAL'),
('ru','риск','риск','entity_type','RiskContext','BUSINESS_TERM','FINAM_CORE_EXPLAINABILITY_KG_ONTOLOGY_V1',1.0,'MANUAL'),
('ru','риски','риски','entity_type','RiskContext','BUSINESS_TERM','FINAM_CORE_EXPLAINABILITY_KG_ONTOLOGY_V1',1.0,'MANUAL'),
('ru','признаки','признаки','entity_type','FeatureContext','BUSINESS_TERM','FINAM_CORE_EXPLAINABILITY_KG_ONTOLOGY_V1',1.0,'MANUAL'),
('ru','факторы','факторы','entity_type','FeatureContext','BUSINESS_TERM','FINAM_CORE_EXPLAINABILITY_KG_ONTOLOGY_V1',0.95,'MANUAL'),
('ru','edge','edge','entity_type','EdgeGate','BUSINESS_TERM','FINAM_CORE_EXPLAINABILITY_KG_ONTOLOGY_V1',1.0,'MANUAL'),
('ru','эдж','эдж','entity_type','EdgeGate','BUSINESS_TERM','FINAM_CORE_EXPLAINABILITY_KG_ONTOLOGY_V1',1.0,'MANUAL'),
('ru','преимущество','преимущество','entity_type','EdgeGate','BUSINESS_TERM','FINAM_CORE_EXPLAINABILITY_KG_ONTOLOGY_V1',0.95,'MANUAL'),

('en','trade','trade','entity_type','ClosedTrade','BUSINESS_TERM','FINAM_CORE_EXPLAINABILITY_KG_ONTOLOGY_V1',0.95,'MANUAL'),
('en','trades','trades','entity_type','ClosedTrade','BUSINESS_TERM','FINAM_CORE_EXPLAINABILITY_KG_ONTOLOGY_V1',1.0,'MANUAL'),
('en','closed trades','closed trades','entity_type','ClosedTrade','BUSINESS_TERM','FINAM_CORE_EXPLAINABILITY_KG_ONTOLOGY_V1',1.0,'MANUAL'),
('en','completed trades','completed trades','entity_type','ClosedTrade','BUSINESS_TERM','FINAM_CORE_EXPLAINABILITY_KG_ONTOLOGY_V1',1.0,'MANUAL'),
('en','fill','fill','entity_type','Fill','BUSINESS_TERM','FINAM_CORE_EXPLAINABILITY_KG_ONTOLOGY_V1',1.0,'MANUAL'),
('en','fills','fills','entity_type','Fill','BUSINESS_TERM','FINAM_CORE_EXPLAINABILITY_KG_ONTOLOGY_V1',1.0,'MANUAL'),
('en','risk','risk','entity_type','RiskContext','BUSINESS_TERM','FINAM_CORE_EXPLAINABILITY_KG_ONTOLOGY_V1',1.0,'MANUAL'),
('en','risks','risks','entity_type','RiskContext','BUSINESS_TERM','FINAM_CORE_EXPLAINABILITY_KG_ONTOLOGY_V1',1.0,'MANUAL'),
('en','features','features','entity_type','FeatureContext','BUSINESS_TERM','FINAM_CORE_EXPLAINABILITY_KG_ONTOLOGY_V1',1.0,'MANUAL'),
('en','factors','factors','entity_type','FeatureContext','BUSINESS_TERM','FINAM_CORE_EXPLAINABILITY_KG_ONTOLOGY_V1',0.95,'MANUAL'),
('en','edge','edge','entity_type','EdgeGate','BUSINESS_TERM','FINAM_CORE_EXPLAINABILITY_KG_ONTOLOGY_V1',1.0,'MANUAL'),
('en','advantage','advantage','entity_type','EdgeGate','BUSINESS_TERM','FINAM_CORE_EXPLAINABILITY_KG_ONTOLOGY_V1',0.95,'MANUAL')
ON CONFLICT DO NOTHING;

CREATE OR REPLACE VIEW knowledge_graph.v_semantic_lookup_v1 AS
SELECT
    locale,
    raw_term,
    normalized_term,
    object_type,
    object_key,
    match_type,
    confidence,
    source,
    ontology_version
FROM knowledge_graph.semantic_terms
WHERE enabled=true;

GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA knowledge_graph TO alex;
GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA knowledge_graph TO alex;

COMMIT;

SELECT 'KNOWLEDGE_GRAPH_SEMANTIC_NORMALIZATION_V1_READY' AS verdict;
