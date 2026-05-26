ALTER TABLE trades
ADD COLUMN IF NOT EXISTS continuous_symbol TEXT;

ALTER TABLE trade_context_snapshots
ADD COLUMN IF NOT EXISTS continuous_symbol TEXT;

CREATE INDEX IF NOT EXISTS idx_trades_continuous_symbol_created
ON trades(continuous_symbol, created_at DESC);

CREATE INDEX IF NOT EXISTS idx_trade_context_snapshots_continuous_symbol_created
ON trade_context_snapshots(continuous_symbol, created_at DESC);
