CREATE TABLE IF NOT EXISTS analytics.strategy_registry_v1 (
    strategy_family TEXT NOT NULL,
    strategy_name TEXT NOT NULL DEFAULT '',
    strategy_version TEXT NOT NULL DEFAULT 'v1',
    category TEXT NOT NULL DEFAULT 'UNKNOWN',
    enabled BOOLEAN NOT NULL DEFAULT false,
    paper_enabled BOOLEAN NOT NULL DEFAULT false,
    risk_enabled BOOLEAN NOT NULL DEFAULT false,
    live_enabled BOOLEAN NOT NULL DEFAULT false,
    priority INTEGER NOT NULL DEFAULT 100,
    description TEXT NOT NULL DEFAULT '',
    status TEXT NOT NULL DEFAULT 'DRAFT',
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    source_version TEXT NOT NULL DEFAULT 'STRATEGY_PLATFORM_FOUNDATION_V1',
    build_id TEXT NOT NULL DEFAULT 'manual',
    PRIMARY KEY (strategy_family, strategy_version)
);

CREATE TABLE IF NOT EXISTS analytics.strategy_configuration_v1 (
    strategy_family TEXT NOT NULL,
    strategy_version TEXT NOT NULL DEFAULT 'v1',
    config_version TEXT NOT NULL DEFAULT 'config_v1',
    active BOOLEAN NOT NULL DEFAULT true,
    config_json JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    source_version TEXT NOT NULL DEFAULT 'STRATEGY_PLATFORM_FOUNDATION_V1',
    build_id TEXT NOT NULL DEFAULT 'manual',
    PRIMARY KEY (strategy_family, strategy_version, config_version)
);

CREATE TABLE IF NOT EXISTS analytics.strategy_feature_dependency_v1 (
    strategy_family TEXT NOT NULL,
    strategy_version TEXT NOT NULL DEFAULT 'v1',
    feature_name TEXT NOT NULL,
    required BOOLEAN NOT NULL DEFAULT true,
    weight NUMERIC(10,4) NOT NULL DEFAULT 1.0,
    source_version TEXT NOT NULL DEFAULT 'STRATEGY_PLATFORM_FOUNDATION_V1',
    build_id TEXT NOT NULL DEFAULT 'manual',
    PRIMARY KEY (strategy_family, strategy_version, feature_name)
);

INSERT INTO analytics.strategy_registry_v1 (
    strategy_family, strategy_name, strategy_version, category,
    enabled, paper_enabled, risk_enabled, live_enabled,
    priority, description, status
)
VALUES (
    'VOLATILITY_BREAKOUT',
    'Volatility Breakout',
    'v1',
    'VOLATILITY',
    true,
    true,
    false,
    false,
    10,
    'Первая стратегия платформы: пробой волатильности на признаках Feature Store.',
    'ACTIVE'
)
ON CONFLICT (strategy_family, strategy_version) DO UPDATE SET
    strategy_name=EXCLUDED.strategy_name,
    category=EXCLUDED.category,
    enabled=EXCLUDED.enabled,
    paper_enabled=EXCLUDED.paper_enabled,
    risk_enabled=EXCLUDED.risk_enabled,
    live_enabled=EXCLUDED.live_enabled,
    priority=EXCLUDED.priority,
    description=EXCLUDED.description,
    status=EXCLUDED.status,
    updated_at=now();

INSERT INTO analytics.strategy_configuration_v1 (
    strategy_family, strategy_version, config_version, active, config_json
)
VALUES (
    'VOLATILITY_BREAKOUT',
    'v1',
    'config_v1',
    true,
    '{
      "min_range_pct": 0.8,
      "min_body_pct": 0.5,
      "min_volume_ratio20": 1.2,
      "min_feature_quality": 0.85,
      "min_return1_pct": 0.0,
      "min_return5_pct": 0.0
    }'::jsonb
)
ON CONFLICT (strategy_family, strategy_version, config_version) DO UPDATE SET
    active=EXCLUDED.active,
    config_json=EXCLUDED.config_json,
    updated_at=now();

INSERT INTO analytics.strategy_feature_dependency_v1 (
    strategy_family, strategy_version, feature_name, required, weight
)
VALUES
    ('VOLATILITY_BREAKOUT','v1','range_pct',true,1.0),
    ('VOLATILITY_BREAKOUT','v1','body_pct',true,1.0),
    ('VOLATILITY_BREAKOUT','v1','volume_ratio20',true,1.0),
    ('VOLATILITY_BREAKOUT','v1','return1_pct',true,0.8),
    ('VOLATILITY_BREAKOUT','v1','return5_pct',true,0.8),
    ('VOLATILITY_BREAKOUT','v1','feature_quality_score',true,1.0)
ON CONFLICT (strategy_family, strategy_version, feature_name) DO UPDATE SET
    required=EXCLUDED.required,
    weight=EXCLUDED.weight;

GRANT USAGE ON SCHEMA analytics TO alex;
GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA analytics TO alex;
