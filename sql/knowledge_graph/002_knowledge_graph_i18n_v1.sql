BEGIN;

CREATE TABLE IF NOT EXISTS knowledge_graph.languages (
    locale TEXT PRIMARY KEY,
    name_native TEXT NOT NULL,
    name_en TEXT NOT NULL,
    enabled BOOLEAN NOT NULL DEFAULT true,
    is_default BOOLEAN NOT NULL DEFAULT false,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS knowledge_graph.i18n_labels (
    label_id BIGSERIAL PRIMARY KEY,
    object_type TEXT NOT NULL,
    object_key TEXT NOT NULL,
    locale TEXT NOT NULL REFERENCES knowledge_graph.languages(locale),
    label TEXT NOT NULL,
    short_label TEXT,
    description TEXT,
    ontology_version TEXT NOT NULL,
    translation_source TEXT NOT NULL DEFAULT 'MANUAL',
    translation_status TEXT NOT NULL DEFAULT 'VERIFIED',
    quality_score NUMERIC(5,4) NOT NULL DEFAULT 1.0,
    verified_by TEXT,
    verified_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE(object_type, object_key, locale, ontology_version)
);

CREATE TABLE IF NOT EXISTS knowledge_graph.i18n_aliases (
    alias_id BIGSERIAL PRIMARY KEY,
    object_type TEXT NOT NULL,
    object_key TEXT NOT NULL,
    locale TEXT NOT NULL REFERENCES knowledge_graph.languages(locale),
    alias TEXT NOT NULL,
    alias_type TEXT NOT NULL DEFAULT 'SYNONYM',
    ontology_version TEXT NOT NULL,
    translation_source TEXT NOT NULL DEFAULT 'MANUAL',
    translation_status TEXT NOT NULL DEFAULT 'VERIFIED',
    quality_score NUMERIC(5,4) NOT NULL DEFAULT 1.0,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE(object_type, object_key, locale, alias, ontology_version)
);

CREATE TABLE IF NOT EXISTS knowledge_graph.translation_providers (
    provider_key TEXT PRIMARY KEY,
    provider_name TEXT NOT NULL,
    provider_type TEXT NOT NULL,
    enabled BOOLEAN NOT NULL DEFAULT false,
    config JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS knowledge_graph.translation_jobs (
    job_id BIGSERIAL PRIMARY KEY,
    provider_key TEXT REFERENCES knowledge_graph.translation_providers(provider_key),
    source_locale TEXT NOT NULL,
    target_locale TEXT NOT NULL,
    object_type TEXT NOT NULL,
    object_key TEXT NOT NULL,
    source_text TEXT NOT NULL,
    translated_text TEXT,
    status TEXT NOT NULL DEFAULT 'NEW',
    quality_score NUMERIC(5,4),
    error TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS knowledge_graph.translation_audit (
    audit_id BIGSERIAL PRIMARY KEY,
    label_id BIGINT,
    action TEXT NOT NULL,
    old_payload JSONB NOT NULL DEFAULT '{}'::jsonb,
    new_payload JSONB NOT NULL DEFAULT '{}'::jsonb,
    actor TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_kg_i18n_labels_lookup_v1
ON knowledge_graph.i18n_labels(object_type, object_key, locale);

CREATE INDEX IF NOT EXISTS idx_kg_i18n_aliases_lookup_v1
ON knowledge_graph.i18n_aliases(locale, alias);

GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA knowledge_graph TO alex;
GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA knowledge_graph TO alex;

INSERT INTO knowledge_graph.languages(locale, name_native, name_en, enabled, is_default)
VALUES
('ru', 'Русский', 'Russian', true, true),
('en', 'English', 'English', true, false)
ON CONFLICT (locale) DO NOTHING;

INSERT INTO knowledge_graph.translation_providers(provider_key, provider_name, provider_type, enabled)
VALUES
('MANUAL', 'Manual review', 'HUMAN', true),
('GOOGLE', 'Google Translate', 'API', false),
('DEEPL', 'DeepL', 'API', false),
('OPENAI', 'OpenAI', 'API', false),
('LOCAL_LLM', 'Local LLM', 'LOCAL', false)
ON CONFLICT (provider_key) DO NOTHING;

INSERT INTO knowledge_graph.i18n_labels
(object_type, object_key, locale, label, short_label, description, ontology_version)
VALUES
('domain','PAPER_RUNTIME','ru','Бумажный Runtime','Paper Runtime','Домен бумажного исполнения и проверки торговых решений.','FINAM_CORE_EXPLAINABILITY_KG_ONTOLOGY_V1'),
('domain','PAPER_RUNTIME','en','Paper Runtime','Paper Runtime','Domain for paper execution and trading decision validation.','FINAM_CORE_EXPLAINABILITY_KG_ONTOLOGY_V1'),

('entity_type','TradeContextSnapshot','ru','Контекст сделки','Контекст сделки','Центральный снимок торгового решения или события исполнения.','FINAM_CORE_EXPLAINABILITY_KG_ONTOLOGY_V1'),
('entity_type','TradeContextSnapshot','en','Trade Context Snapshot','Trade Context','Central snapshot of a trading decision or execution event.','FINAM_CORE_EXPLAINABILITY_KG_ONTOLOGY_V1'),

('entity_type','Attribution','ru','Атрибуция','Атрибуция','Происхождение торгового действия, сигнала или исполнения.','FINAM_CORE_EXPLAINABILITY_KG_ONTOLOGY_V1'),
('entity_type','Attribution','en','Attribution','Attribution','Origin of a trading action, signal, or execution.','FINAM_CORE_EXPLAINABILITY_KG_ONTOLOGY_V1'),

('entity_type','RiskContext','ru','Контекст риска','Риск','Контекст риск-контроля для сделки или решения.','FINAM_CORE_EXPLAINABILITY_KG_ONTOLOGY_V1'),
('entity_type','RiskContext','en','Risk Context','Risk','Risk control context for a trade or decision.','FINAM_CORE_EXPLAINABILITY_KG_ONTOLOGY_V1'),

('entity_type','FeatureContext','ru','Контекст признаков','Признаки','Рыночные и модельные признаки, использованные при решении.','FINAM_CORE_EXPLAINABILITY_KG_ONTOLOGY_V1'),
('entity_type','FeatureContext','en','Feature Context','Features','Market and model features used in a decision.','FINAM_CORE_EXPLAINABILITY_KG_ONTOLOGY_V1'),

('entity_type','EdgeGate','ru','Фильтр преимущества','Edge Gate','Решение о наличии или отсутствии подтверждённого преимущества.','FINAM_CORE_EXPLAINABILITY_KG_ONTOLOGY_V1'),
('entity_type','EdgeGate','en','Edge Gate','Edge Gate','Decision on whether a validated edge exists.','FINAM_CORE_EXPLAINABILITY_KG_ONTOLOGY_V1'),

('entity_type','Fill','ru','Исполнение','Fill','Факт исполнения бумажной сделки.','FINAM_CORE_EXPLAINABILITY_KG_ONTOLOGY_V1'),
('entity_type','Fill','en','Fill','Fill','Paper execution event.','FINAM_CORE_EXPLAINABILITY_KG_ONTOLOGY_V1'),

('entity_type','ClosedTrade','ru','Закрытая сделка','Closed Trade','Завершённая сделка с финансовым результатом.','FINAM_CORE_EXPLAINABILITY_KG_ONTOLOGY_V1'),
('entity_type','ClosedTrade','en','Closed Trade','Closed Trade','Completed trade with financial result.','FINAM_CORE_EXPLAINABILITY_KG_ONTOLOGY_V1'),

('edge_type','HAS_ATTRIBUTION','ru','имеет атрибуцию','Атрибуция','Связывает контекст сделки с происхождением действия.','FINAM_CORE_EXPLAINABILITY_KG_ONTOLOGY_V1'),
('edge_type','HAS_ATTRIBUTION','en','has attribution','Attribution','Links trade context to action origin.','FINAM_CORE_EXPLAINABILITY_KG_ONTOLOGY_V1'),

('edge_type','HAS_RISK_CONTEXT','ru','имеет контекст риска','Риск','Связывает контекст сделки с риск-контекстом.','FINAM_CORE_EXPLAINABILITY_KG_ONTOLOGY_V1'),
('edge_type','HAS_RISK_CONTEXT','en','has risk context','Risk','Links trade context to risk context.','FINAM_CORE_EXPLAINABILITY_KG_ONTOLOGY_V1'),

('edge_type','PRODUCED_FILL','ru','произвёл исполнение','Исполнение','Связывает торговый контекст с исполнением.','FINAM_CORE_EXPLAINABILITY_KG_ONTOLOGY_V1'),
('edge_type','PRODUCED_FILL','en','produced fill','Fill','Links trade context to execution fill.','FINAM_CORE_EXPLAINABILITY_KG_ONTOLOGY_V1')
ON CONFLICT DO NOTHING;

INSERT INTO knowledge_graph.i18n_aliases
(object_type, object_key, locale, alias, alias_type, ontology_version)
VALUES
('entity_type','TradeContextSnapshot','ru','контекст торговой операции','SYNONYM','FINAM_CORE_EXPLAINABILITY_KG_ONTOLOGY_V1'),
('entity_type','TradeContextSnapshot','ru','контекст исполнения сделки','SYNONYM','FINAM_CORE_EXPLAINABILITY_KG_ONTOLOGY_V1'),
('entity_type','TradeContextSnapshot','en','trade snapshot','SYNONYM','FINAM_CORE_EXPLAINABILITY_KG_ONTOLOGY_V1'),
('entity_type','TradeContextSnapshot','en','execution snapshot','SYNONYM','FINAM_CORE_EXPLAINABILITY_KG_ONTOLOGY_V1'),
('entity_type','Fill','ru','исполненная заявка','SYNONYM','FINAM_CORE_EXPLAINABILITY_KG_ONTOLOGY_V1'),
('entity_type','ClosedTrade','ru','завершенная сделка','SYNONYM','FINAM_CORE_EXPLAINABILITY_KG_ONTOLOGY_V1'),
('entity_type','ClosedTrade','en','completed trade','SYNONYM','FINAM_CORE_EXPLAINABILITY_KG_ONTOLOGY_V1')
ON CONFLICT DO NOTHING;

COMMIT;

SELECT 'KNOWLEDGE_GRAPH_I18N_V1_READY' AS verdict;
