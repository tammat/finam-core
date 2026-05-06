CREATE TABLE IF NOT EXISTS position_intents (
    symbol TEXT PRIMARY KEY,
    horizon TEXT NOT NULL CHECK (horizon IN ('intraday', 'swing', 'long_term')),
    allow_intraday_exit BOOLEAN NOT NULL DEFAULT false,
    allow_trailing BOOLEAN NOT NULL DEFAULT false,
    allow_new_buy BOOLEAN NOT NULL DEFAULT false,
    enabled BOOLEAN NOT NULL DEFAULT true,
    comment TEXT,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS position_intent_history (
    id BIGSERIAL PRIMARY KEY,
    symbol TEXT NOT NULL,
    old_horizon TEXT,
    new_horizon TEXT NOT NULL,
    old_enabled BOOLEAN,
    new_enabled BOOLEAN NOT NULL,
    comment TEXT,
    changed_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
