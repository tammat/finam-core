ALTER TABLE trades
ADD COLUMN IF NOT EXISTS trade_source text DEFAULT 'unknown';

UPDATE trades
SET trade_source = 'manual'
WHERE COALESCE(trade_source, 'unknown') = 'unknown';

CREATE INDEX IF NOT EXISTS idx_trades_trade_source
ON trades (trade_source);

CREATE INDEX IF NOT EXISTS idx_trades_symbol_trade_source
ON trades (symbol, trade_source);
