CREATE TABLE IF NOT EXISTS strategy_scorecard_daily (
    trade_date DATE NOT NULL,
    strategy TEXT NOT NULL,
    symbol TEXT NOT NULL,
    timeframe TEXT NOT NULL DEFAULT 'unknown',

    trades INTEGER NOT NULL,
    gross_pnl NUMERIC NOT NULL,
    net_pnl NUMERIC NOT NULL,
    winrate NUMERIC NOT NULL,
    profit_factor NUMERIC NOT NULL,
    avg_win NUMERIC NOT NULL,
    avg_loss NUMERIC NOT NULL,
    expectancy NUMERIC NOT NULL,
    max_drawdown NUMERIC NOT NULL,
    avg_r NUMERIC NOT NULL,
    commission_total NUMERIC NOT NULL,

    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),

    PRIMARY KEY (trade_date, strategy, symbol, timeframe)
);
