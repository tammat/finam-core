INSERT INTO knowledge.recommendation_direction_v1
(direction_code, direction_name, enabled, source_version)
VALUES
('DIRECTION_UP', 'Upward research direction', TRUE, 'RECOMMENDATION_EXECUTION_CONTEXT_SCHEMA_V1'),
('DIRECTION_DOWN', 'Downward research direction', TRUE, 'RECOMMENDATION_EXECUTION_CONTEXT_SCHEMA_V1'),
('DIRECTION_NEUTRAL', 'Neutral research direction', TRUE, 'RECOMMENDATION_EXECUTION_CONTEXT_SCHEMA_V1')
ON CONFLICT(direction_code)
DO UPDATE SET
    direction_name=EXCLUDED.direction_name,
    enabled=EXCLUDED.enabled,
    source_version=EXCLUDED.source_version,
    updated_at=now();
