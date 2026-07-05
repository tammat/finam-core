ALTER TABLE analytics.strategy_library_v1
ADD COLUMN IF NOT EXISTS engine_name TEXT NOT NULL DEFAULT 'UNASSIGNED_ENGINE';

CREATE TABLE IF NOT EXISTS analytics.strategy_engine_registry_v1 (
    engine_name TEXT PRIMARY KEY,
    engine_version TEXT NOT NULL DEFAULT 'v1',
    engine_family TEXT NOT NULL DEFAULT 'GENERIC',
    enabled BOOLEAN NOT NULL DEFAULT true,
    config_json JSONB NOT NULL DEFAULT '{}'::jsonb,
    source_version TEXT NOT NULL DEFAULT 'STRATEGY_DISPATCHER_V1',
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

INSERT INTO analytics.strategy_engine_registry_v1 (
    engine_name, engine_version, engine_family, enabled, config_json
)
VALUES (
    'UNASSIGNED_ENGINE', 'v1', 'GENERIC', true, '{}'::jsonb
)
ON CONFLICT(engine_name) DO UPDATE SET
    enabled=EXCLUDED.enabled,
    updated_at=now();

GRANT SELECT, INSERT, UPDATE, DELETE ON analytics.strategy_engine_registry_v1 TO alex;
