CREATE TABLE IF NOT EXISTS analytics.parameter_search_space_v1 (
    id BIGSERIAL PRIMARY KEY,
    strategy_code TEXT NOT NULL,
    parameter_name TEXT NOT NULL,
    parameter_type TEXT NOT NULL DEFAULT 'float',
    min_value NUMERIC(20,8),
    max_value NUMERIC(20,8),
    step_value NUMERIC(20,8),
    allowed_values JSONB NOT NULL DEFAULT '[]'::jsonb,
    search_method TEXT NOT NULL DEFAULT 'GRID',
    enabled BOOLEAN NOT NULL DEFAULT true,
    source_version TEXT NOT NULL DEFAULT 'PARAMETER_SEARCH_FOUNDATION_V1',
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE(strategy_code, parameter_name)
);

CREATE TABLE IF NOT EXISTS analytics.parameter_search_job_v1 (
    id BIGSERIAL PRIMARY KEY,
    search_code TEXT NOT NULL UNIQUE,
    strategy_code TEXT NOT NULL,
    symbol TEXT NOT NULL,
    timeframe TEXT NOT NULL,
    method_code TEXT NOT NULL DEFAULT 'GRID',
    status_code TEXT NOT NULL DEFAULT 'QUEUED',
    max_trials INTEGER NOT NULL DEFAULT 100,
    objective_metric TEXT NOT NULL DEFAULT 'normalized_edge_score',
    source_version TEXT NOT NULL DEFAULT 'PARAMETER_SEARCH_FOUNDATION_V1',
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

GRANT SELECT, INSERT, UPDATE, DELETE ON analytics.parameter_search_space_v1 TO alex;
GRANT SELECT, INSERT, UPDATE, DELETE ON analytics.parameter_search_job_v1 TO alex;
GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA analytics TO alex;
