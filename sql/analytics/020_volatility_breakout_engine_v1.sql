INSERT INTO analytics.strategy_engine_registry_v1 (
    engine_name,
    engine_version,
    engine_family,
    enabled,
    config_json,
    source_version,
    updated_at
)
VALUES (
    'VOLATILITY_BREAKOUT_ENGINE_V1',
    'v1',
    'BREAKOUT',
    true,
    '{"default_lookback":20,"default_threshold":0.0}'::jsonb,
    'VOLATILITY_BREAKOUT_ENGINE_V1',
    now()
)
ON CONFLICT(engine_name) DO UPDATE SET
    engine_version=EXCLUDED.engine_version,
    engine_family=EXCLUDED.engine_family,
    enabled=EXCLUDED.enabled,
    config_json=EXCLUDED.config_json,
    source_version=EXCLUDED.source_version,
    updated_at=now();

UPDATE analytics.strategy_library_v1
SET engine_name='VOLATILITY_BREAKOUT_ENGINE_V1',
    updated_at=now()
WHERE strategy_code IN (
    'VOLATILITY_BREAKOUT_V2',
    'OPENING_RANGE_BREAKOUT_V1',
    'NR7_BREAKOUT_V1'
);

GRANT SELECT, INSERT, UPDATE, DELETE ON analytics.strategy_engine_registry_v1 TO alex;
