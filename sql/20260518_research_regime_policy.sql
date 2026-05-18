CREATE TABLE IF NOT EXISTS research_regime_policy (
    id BIGSERIAL PRIMARY KEY,
    policy_id TEXT NOT NULL,
    campaign_pattern TEXT NOT NULL,
    regime TEXT NOT NULL,
    trend TEXT NOT NULL,
    volatility TEXT NOT NULL,
    decision TEXT NOT NULL,
    risk_multiplier DOUBLE PRECISION NOT NULL DEFAULT 0,
    reason TEXT NOT NULL DEFAULT '',
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    raw_json JSONB NOT NULL DEFAULT '{}'::jsonb
);

CREATE INDEX IF NOT EXISTS idx_research_regime_policy_policy_id
    ON research_regime_policy(policy_id);

CREATE INDEX IF NOT EXISTS idx_research_regime_policy_regime
    ON research_regime_policy(regime);

CREATE INDEX IF NOT EXISTS idx_research_regime_policy_created_at
    ON research_regime_policy(created_at);
