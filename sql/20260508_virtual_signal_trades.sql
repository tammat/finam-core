CREATE TABLE IF NOT EXISTS virtual_signal_trades (
    id BIGSERIAL PRIMARY KEY,
    symbol TEXT NOT NULL,
    side TEXT NOT NULL,
    qty DOUBLE PRECISION NOT NULL,
    entry_price DOUBLE PRECISION NOT NULL,
    stop_loss DOUBLE PRECISION NOT NULL,
    take_profit DOUBLE PRECISION NOT NULL,
    status TEXT NOT NULL DEFAULT 'OPEN',
    opened_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    closed_at TIMESTAMPTZ,
    exit_price DOUBLE PRECISION,
    close_reason TEXT,
    pnl DOUBLE PRECISION DEFAULT 0,
    r_multiple DOUBLE PRECISION DEFAULT 0,
    raw_json JSONB NOT NULL DEFAULT '{}'::jsonb
);

CREATE INDEX IF NOT EXISTS idx_virtual_signal_trades_symbol_status
    ON virtual_signal_trades (symbol, status);

CREATE INDEX IF NOT EXISTS idx_virtual_signal_trades_opened_at
    ON virtual_signal_trades (opened_at DESC);
