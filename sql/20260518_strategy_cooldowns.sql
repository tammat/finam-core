CREATE TABLE IF NOT EXISTS strategy_cooldowns (
    strategy TEXT NOT NULL,
    symbol TEXT NOT NULL,
    timeframe TEXT NOT NULL DEFAULT 'unknown',

    decision TEXT NOT NULL,
    reason TEXT NOT NULL DEFAULT 'unknown',

    cooldown_until TIMESTAMPTZ NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),

    PRIMARY KEY (strategy, symbol, timeframe)
);

CREATE INDEX IF NOT EXISTS idx_strategy_cooldowns_until
    ON strategy_cooldowns (cooldown_until DESC);

CREATE INDEX IF NOT EXISTS idx_strategy_cooldowns_symbol
    ON strategy_cooldowns (symbol);
