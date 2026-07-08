CREATE UNIQUE INDEX IF NOT EXISTS ux_relationship_correlation_collector_v1
ON knowledge.relationship_v1
(source_type, source_code, relation_type, target_type, target_code, source_version)
WHERE source_version='MARKET_CONTEXT_CORRELATION_COLLECTOR_V1';
