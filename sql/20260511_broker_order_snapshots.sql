CREATE TABLE IF NOT EXISTS broker_order_snapshots (
    id bigserial PRIMARY KEY,
    ts timestamptz NOT NULL DEFAULT now(),
    order_id text,
    symbol text NOT NULL DEFAULT '',
    side text NOT NULL DEFAULT '',
    status text NOT NULL DEFAULT '',
    qty double precision NOT NULL DEFAULT 0,
    filled_qty double precision NOT NULL DEFAULT 0,
    remaining_qty double precision NOT NULL DEFAULT 0,
    source text NOT NULL DEFAULT 'finam_get_orders',
    raw jsonb NOT NULL DEFAULT '{}'::jsonb
);

CREATE INDEX IF NOT EXISTS idx_broker_order_snapshots_ts
ON broker_order_snapshots(ts DESC);

CREATE INDEX IF NOT EXISTS idx_broker_order_snapshots_order_id_ts
ON broker_order_snapshots(order_id, ts DESC);

CREATE INDEX IF NOT EXISTS idx_broker_order_snapshots_symbol_ts
ON broker_order_snapshots(symbol, ts DESC);

CREATE INDEX IF NOT EXISTS idx_broker_order_snapshots_status_ts
ON broker_order_snapshots(status, ts DESC);
