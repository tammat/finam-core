BEGIN;

CREATE TABLE IF NOT EXISTS marketcore_ui.paper_runtime_summary_v1 (
    id SMALLINT PRIMARY KEY,
    paper_status TEXT NOT NULL DEFAULT 'READY',
    closed_trades_total INTEGER NOT NULL DEFAULT 0,
    closed_trades_today INTEGER NOT NULL DEFAULT 0,
    signals_today INTEGER NOT NULL DEFAULT 0,
    fills_today INTEGER NOT NULL DEFAULT 0,
    signal_fills_today INTEGER NOT NULL DEFAULT 0,
    active_symbols INTEGER NOT NULL DEFAULT 0,
    pnl_today NUMERIC(20,2) NOT NULL DEFAULT 0,
    pnl_total NUMERIC(20,2) NOT NULL DEFAULT 0,
    last_closed_trade_at TIMESTAMPTZ,
    refreshed_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    source_version TEXT NOT NULL DEFAULT 'PAPER_RUNTIME_REAL_DATA_V1',
    build_id TEXT NOT NULL DEFAULT 'manual'
);

INSERT INTO marketcore_ui.paper_runtime_summary_v1 (id)
VALUES (1)
ON CONFLICT (id) DO NOTHING;

GRANT USAGE ON SCHEMA marketcore_ui TO alex;
GRANT SELECT ON marketcore_ui.paper_runtime_summary_v1 TO alex;

COMMIT;

GRANT INSERT, UPDATE, DELETE ON marketcore_ui.paper_runtime_summary_v1 TO alex;
