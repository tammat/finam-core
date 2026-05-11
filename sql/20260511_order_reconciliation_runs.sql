CREATE TABLE IF NOT EXISTS order_reconciliation_runs (
    id bigserial PRIMARY KEY,
    ts timestamptz NOT NULL DEFAULT now(),
    acks_count integer NOT NULL DEFAULT 0,
    broker_orders_count integer NOT NULL DEFAULT 0,
    issues_count integer NOT NULL DEFAULT 0,
    status text NOT NULL,
    source text NOT NULL DEFAULT 'order_ack_reconcile_timer',
    raw jsonb NOT NULL DEFAULT '{}'::jsonb
);

CREATE TABLE IF NOT EXISTS order_reconciliation_issues (
    id bigserial PRIMARY KEY,
    run_id bigint NOT NULL REFERENCES order_reconciliation_runs(id) ON DELETE CASCADE,
    ts timestamptz NOT NULL DEFAULT now(),
    order_id text,
    symbol text NOT NULL,
    issue_type text NOT NULL,
    reason text NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_order_reconciliation_runs_ts ON order_reconciliation_runs(ts DESC);
CREATE INDEX IF NOT EXISTS idx_order_reconciliation_runs_status ON order_reconciliation_runs(status);
CREATE INDEX IF NOT EXISTS idx_order_reconciliation_issues_run_id ON order_reconciliation_issues(run_id);
CREATE INDEX IF NOT EXISTS idx_order_reconciliation_issues_order_id ON order_reconciliation_issues(order_id);
CREATE INDEX IF NOT EXISTS idx_order_reconciliation_issues_symbol_ts ON order_reconciliation_issues(symbol, ts DESC);
