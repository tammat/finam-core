CREATE TABLE IF NOT EXISTS oms_order_journal (
    id BIGSERIAL PRIMARY KEY,
    client_order_id TEXT NOT NULL UNIQUE,
    broker_order_id TEXT,
    symbol TEXT NOT NULL,
    side TEXT NOT NULL,
    qty DOUBLE PRECISION NOT NULL,
    price DOUBLE PRECISION,
    order_type TEXT NOT NULL DEFAULT 'MARKET',
    status TEXT NOT NULL,
    source TEXT NOT NULL DEFAULT 'pipeline',
    payload JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_oms_order_journal_symbol
ON oms_order_journal(symbol);

CREATE INDEX IF NOT EXISTS idx_oms_order_journal_status
ON oms_order_journal(status);
