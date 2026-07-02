BEGIN;

CREATE TABLE IF NOT EXISTS knowledge_graph.validation_runs (
    run_id BIGSERIAL PRIMARY KEY,
    domain TEXT,
    status TEXT NOT NULL DEFAULT 'STARTED',
    started_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    finished_at TIMESTAMPTZ,
    total_findings INTEGER NOT NULL DEFAULT 0,
    payload JSONB NOT NULL DEFAULT '{}'::jsonb
);

CREATE TABLE IF NOT EXISTS knowledge_graph.validation_findings (
    finding_id BIGSERIAL PRIMARY KEY,
    run_id BIGINT NOT NULL REFERENCES knowledge_graph.validation_runs(run_id) ON DELETE CASCADE,
    domain TEXT,
    check_code TEXT NOT NULL,
    severity TEXT NOT NULL,
    object_type TEXT,
    object_key TEXT,
    details JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_kg_validation_findings_run_v1
ON knowledge_graph.validation_findings(run_id);

CREATE INDEX IF NOT EXISTS idx_kg_validation_findings_code_v1
ON knowledge_graph.validation_findings(check_code);

GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA knowledge_graph TO alex;
GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA knowledge_graph TO alex;

COMMIT;

SELECT 'KNOWLEDGE_GRAPH_VALIDATION_SCHEMA_V1_READY' AS verdict;
