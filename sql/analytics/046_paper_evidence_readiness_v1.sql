CREATE TABLE IF NOT EXISTS analytics.paper_evidence_readiness_v1 (
    regime TEXT NOT NULL,
    timeframe TEXT NOT NULL,
    closed_trades INTEGER NOT NULL,
    trading_sessions INTEGER NOT NULL,
    required_closed_trades INTEGER NOT NULL,
    required_trading_sessions INTEGER NOT NULL,
    missing_closed_trades INTEGER NOT NULL,
    missing_trading_sessions INTEGER NOT NULL,
    net_profit_factor NUMERIC,
    net_expectancy NUMERIC,
    max_drawdown NUMERIC,
    evidence_ready BOOLEAN NOT NULL,
    policy_version TEXT NOT NULL,
    refreshed_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    PRIMARY KEY (regime, timeframe)
);

COMMENT ON TABLE analytics.paper_evidence_readiness_v1 IS
'Paper evidence gate by regime and timeframe. Thresholds are loaded from versioned policy, never embedded in SQL.';

GRANT SELECT, INSERT, UPDATE, DELETE ON analytics.paper_evidence_readiness_v1 TO alex;
GRANT SELECT, INSERT, UPDATE, DELETE ON analytics.paper_evidence_readiness_v1 TO finam;
