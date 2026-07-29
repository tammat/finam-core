-- Do not wrap this migration in a transaction: CONCURRENTLY keeps collectors writable.
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_market_bars_symbol_ts_close_v1
ON market_bars(symbol,ts DESC) INCLUDE(close);

CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_signals_filled_today_entry_v1
ON signals(created_at DESC,signal_id)
WHERE status='FILLED';
