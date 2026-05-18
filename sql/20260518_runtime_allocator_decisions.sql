CREATE TABLE IF NOT EXISTS runtime_allocator_decisions (
    id BIGSERIAL PRIMARY KEY,

    decision_ts TIMESTAMPTZ NOT NULL DEFAULT now(),

    symbol TEXT NOT NULL,
    strategy TEXT,
    regime TEXT,

    base_score NUMERIC NOT NULL DEFAULT 0,
    strategy_weight NUMERIC NOT NULL DEFAULT 0,
    effective_score NUMERIC NOT NULL DEFAULT 0,

    selected BOOLEAN NOT NULL DEFAULT false,
    decision_reason TEXT NOT NULL DEFAULT 'unknown',

    source TEXT NOT NULL DEFAULT 'runtime_universe_allocator_v2',
    raw_json JSONB NOT NULL DEFAULT '{}'::jsonb
);

CREATE INDEX IF NOT EXISTS idx_runtime_allocator_decisions_ts
    ON runtime_allocator_decisions (decision_ts DESC);

CREATE INDEX IF NOT EXISTS idx_runtime_allocator_decisions_symbol_ts
    ON runtime_allocator_decisions (symbol, decision_ts DESC);

CREATE INDEX IF NOT EXISTS idx_runtime_allocator_decisions_selected
    ON runtime_allocator_decisions (selected, decision_ts DESC);
