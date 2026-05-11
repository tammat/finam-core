CREATE TABLE IF NOT EXISTS order_acks (
    id bigserial PRIMARY KEY,
    ts timestamptz NOT NULL DEFAULT now(),
    symbol text NOT NULL,
    side text NOT NULL,
    qty double precision NOT NULL,
    order_id text,
    status text NOT NULL,
    reason text,
    source text NOT NULL DEFAULT 'finam_orders_client',
    raw jsonb NOT NULL DEFAULT '{}'::jsonb
);

CREATE INDEX IF NOT EXISTS idx_order_acks_ts ON order_acks(ts DESC);
CREATE INDEX IF NOT EXISTS idx_order_acks_symbol_ts ON order_acks(symbol, ts DESC);
CREATE INDEX IF NOT EXISTS idx_order_acks_order_id ON order_acks(order_id);
