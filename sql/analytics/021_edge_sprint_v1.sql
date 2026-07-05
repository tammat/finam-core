CREATE TABLE IF NOT EXISTS analytics.edge_sprint_v1 (
    sprint_code TEXT PRIMARY KEY,
    sprint_name TEXT NOT NULL,
    status_code TEXT NOT NULL DEFAULT 'OPEN',
    objective_metric TEXT NOT NULL DEFAULT 'normalized_edge_score',
    target_observations INTEGER NOT NULL DEFAULT 1000,
    target_candidates INTEGER NOT NULL DEFAULT 10,
    notes TEXT NOT NULL DEFAULT '',
    source_version TEXT NOT NULL DEFAULT 'EDGE_SPRINT_V1',
    started_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    finished_at TIMESTAMPTZ,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS analytics.edge_sprint_snapshot_v1 (
    id BIGSERIAL PRIMARY KEY,
    sprint_code TEXT NOT NULL REFERENCES analytics.edge_sprint_v1(sprint_code),
    observations_total INTEGER NOT NULL DEFAULT 0,
    observations_with_trades INTEGER NOT NULL DEFAULT 0,
    candidates_total INTEGER NOT NULL DEFAULT 0,
    best_score NUMERIC(12,6) NOT NULL DEFAULT 0,
    best_profit_factor NUMERIC(12,6) NOT NULL DEFAULT 0,
    best_expectancy NUMERIC(20,8) NOT NULL DEFAULT 0,
    research_trades INTEGER NOT NULL DEFAULT 0,
    source_version TEXT NOT NULL DEFAULT 'EDGE_SPRINT_V1',
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

GRANT SELECT, INSERT, UPDATE, DELETE ON analytics.edge_sprint_v1 TO alex;
GRANT SELECT, INSERT, UPDATE, DELETE ON analytics.edge_sprint_snapshot_v1 TO alex;
GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA analytics TO alex;
