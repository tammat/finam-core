CREATE TABLE IF NOT EXISTS strategy_rank_decisions (
    trade_date DATE NOT NULL,
    strategy TEXT NOT NULL,
    symbol TEXT NOT NULL,
    timeframe TEXT NOT NULL,

    decision TEXT NOT NULL,
    score NUMERIC NOT NULL,
    reason TEXT NOT NULL,

    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),

    PRIMARY KEY (trade_date, strategy, symbol, timeframe)
);
