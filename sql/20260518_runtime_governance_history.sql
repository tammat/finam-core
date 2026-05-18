CREATE TABLE IF NOT EXISTS runtime_governance_history (
    id BIGSERIAL PRIMARY KEY,

    cycle_ts TIMESTAMPTZ NOT NULL DEFAULT now(),
    trade_date DATE NOT NULL,

    scorecards_saved INTEGER NOT NULL DEFAULT 0,
    rank_decisions_saved INTEGER NOT NULL DEFAULT 0,
    cooldowns_saved INTEGER NOT NULL DEFAULT 0,
    allocation_count INTEGER NOT NULL DEFAULT 0,

    strategies_enabled INTEGER NOT NULL DEFAULT 0,
    strategies_reduced INTEGER NOT NULL DEFAULT 0,
    strategies_disabled INTEGER NOT NULL DEFAULT 0,
    strategies_watch INTEGER NOT NULL DEFAULT 0,

    active_cooldowns INTEGER NOT NULL DEFAULT 0,

    source TEXT NOT NULL DEFAULT 'runtime_governance_service',
    raw_json JSONB NOT NULL DEFAULT '{}'::jsonb
);

CREATE INDEX IF NOT EXISTS idx_runtime_governance_history_ts
    ON runtime_governance_history (cycle_ts DESC);

CREATE INDEX IF NOT EXISTS idx_runtime_governance_history_trade_date
    ON runtime_governance_history (trade_date DESC);
