BEGIN;

CREATE TABLE IF NOT EXISTS marketcore_ui.paper_runtime_equity_curve_v1 (
    point_no INTEGER PRIMARY KEY,
    ts TIMESTAMPTZ NOT NULL,
    ticker TEXT NOT NULL,
    source TEXT NOT NULL,
    realized_pnl NUMERIC(20,6) NOT NULL DEFAULT 0,
    equity_pnl NUMERIC(20,6) NOT NULL DEFAULT 0,
    refreshed_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS marketcore_ui.paper_runtime_drawdown_curve_v1 (
    point_no INTEGER PRIMARY KEY,
    ts TIMESTAMPTZ NOT NULL,
    ticker TEXT NOT NULL,
    source TEXT NOT NULL,
    equity_pnl NUMERIC(20,6) NOT NULL DEFAULT 0,
    peak_equity_pnl NUMERIC(20,6) NOT NULL DEFAULT 0,
    drawdown NUMERIC(20,6) NOT NULL DEFAULT 0,
    drawdown_pct NUMERIC(20,6) NOT NULL DEFAULT 0,
    refreshed_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

GRANT SELECT, INSERT, UPDATE, DELETE ON marketcore_ui.paper_runtime_equity_curve_v1 TO alex;
GRANT SELECT, INSERT, UPDATE, DELETE ON marketcore_ui.paper_runtime_drawdown_curve_v1 TO alex;

COMMIT;
