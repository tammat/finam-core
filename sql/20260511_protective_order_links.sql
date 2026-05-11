CREATE TABLE IF NOT EXISTS protective_order_links (
    id bigserial PRIMARY KEY,
    ts timestamptz NOT NULL DEFAULT now(),
    symbol text NOT NULL,
    side text NOT NULL,
    qty double precision NOT NULL DEFAULT 0,
    entry_order_id text NOT NULL,
    stop_order_id text,
    take_order_id text,
    status text NOT NULL DEFAULT 'OPEN',
    source text NOT NULL DEFAULT 'finam_core',
    raw jsonb NOT NULL DEFAULT '{}'::jsonb
);

CREATE INDEX IF NOT EXISTS idx_protective_order_links_ts ON protective_order_links(ts DESC);
CREATE INDEX IF NOT EXISTS idx_protective_order_links_symbol_ts ON protective_order_links(symbol, ts DESC);
CREATE INDEX IF NOT EXISTS idx_protective_order_links_entry_order_id ON protective_order_links(entry_order_id);
CREATE INDEX IF NOT EXISTS idx_protective_order_links_stop_order_id ON protective_order_links(stop_order_id);
CREATE INDEX IF NOT EXISTS idx_protective_order_links_take_order_id ON protective_order_links(take_order_id);
CREATE INDEX IF NOT EXISTS idx_protective_order_links_status ON protective_order_links(status);
