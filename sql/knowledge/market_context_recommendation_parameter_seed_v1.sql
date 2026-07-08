INSERT INTO knowledge.platform_parameter_v1
(
    parameter_code,
    parameter_name,
    parameter_group,
    parameter_type,
    parameter_value,
    description,
    enabled,
    source_version
)
VALUES
('PROFILE_DEFAULT',                 'Default recommendation profile',      'PROFILE',        'TEXT',    'ACTIVE', 'Default active recommendation profile', TRUE, 'MARKET_CONTEXT_RECOMMENDATION_PARAMETER_SEED_V1'),

('EDGE_VALIDATE_THRESHOLD',         'Edge validation threshold',           'RECOMMENDATION', 'NUMERIC', '80',     'Minimum Edge Score for VALIDATE', TRUE, 'MARKET_CONTEXT_RECOMMENDATION_PARAMETER_SEED_V1'),
('EDGE_RESEARCH_THRESHOLD',         'Edge research threshold',             'RECOMMENDATION', 'NUMERIC', '70',     'Minimum Edge Score for CONTINUE_RESEARCH', TRUE, 'MARKET_CONTEXT_RECOMMENDATION_PARAMETER_SEED_V1'),
('EDGE_OBSERVE_THRESHOLD',          'Edge observe threshold',              'RECOMMENDATION', 'NUMERIC', '50',     'Minimum Edge Score for OBSERVE', TRUE, 'MARKET_CONTEXT_RECOMMENDATION_PARAMETER_SEED_V1'),

('KNOWLEDGE_MIN_THRESHOLD',         'Knowledge minimum coverage',          'KNOWLEDGE',      'NUMERIC', '80',     'Minimum Knowledge Coverage', TRUE, 'MARKET_CONTEXT_RECOMMENDATION_PARAMETER_SEED_V1'),

('MIN_REASONS_REQUIRED',            'Minimum recommendation reasons',      'RECOMMENDATION', 'INTEGER', '3',      'Recommendation must contain at least this many reasons', TRUE, 'MARKET_CONTEXT_RECOMMENDATION_PARAMETER_SEED_V1'),

('MIN_CONFIDENCE_REQUIRED',         'Minimum recommendation confidence',   'RECOMMENDATION', 'NUMERIC', '0.70',   'Minimum confidence', TRUE, 'MARKET_CONTEXT_RECOMMENDATION_PARAMETER_SEED_V1')

ON CONFLICT(parameter_code)
DO UPDATE SET
    parameter_name  = EXCLUDED.parameter_name,
    parameter_group = EXCLUDED.parameter_group,
    parameter_type  = EXCLUDED.parameter_type,
    parameter_value = EXCLUDED.parameter_value,
    description     = EXCLUDED.description,
    enabled         = EXCLUDED.enabled,
    updated_at      = now(),
    source_version  = EXCLUDED.source_version;
