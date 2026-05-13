#!/usr/bin/env bash
set -euo pipefail

sudo -u postgres psql -d finam_core <<'SQL'
CREATE TABLE IF NOT EXISTS signals (
    id BIGSERIAL PRIMARY KEY,
    signal_id TEXT UNIQUE NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),

    symbol TEXT NOT NULL,
    side TEXT NOT NULL,

    strategy TEXT,
    horizon TEXT,
    timeframe TEXT,
    regime TEXT,

    entry_price DOUBLE PRECISION,
    stop_loss DOUBLE PRECISION,
    take_profit DOUBLE PRECISION,

    rr DOUBLE PRECISION,
    confidence DOUBLE PRECISION,

    status TEXT NOT NULL DEFAULT 'NEW',
    rejection_reason TEXT,

    payload JSONB NOT NULL DEFAULT '{}'::jsonb
);

CREATE INDEX IF NOT EXISTS idx_signals_symbol_created_at
ON signals(symbol, created_at DESC);

CREATE INDEX IF NOT EXISTS idx_signals_status
ON signals(status);

CREATE INDEX IF NOT EXISTS idx_signals_horizon
ON signals(horizon);

CREATE TABLE IF NOT EXISTS signal_fills (
    id BIGSERIAL PRIMARY KEY,
    signal_id TEXT NOT NULL,
    fill_id TEXT,

    symbol TEXT NOT NULL,
    side TEXT NOT NULL,

    qty DOUBLE PRECISION NOT NULL,
    price DOUBLE PRECISION NOT NULL,

    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_signal_fills_signal_id
ON signal_fills(signal_id);

CREATE TABLE IF NOT EXISTS closed_trades (
    id BIGSERIAL PRIMARY KEY,
    signal_id TEXT,

    symbol TEXT NOT NULL,
    side TEXT NOT NULL,

    entry_price DOUBLE PRECISION NOT NULL,
    exit_price DOUBLE PRECISION NOT NULL,

    qty DOUBLE PRECISION NOT NULL,

    gross_pnl DOUBLE PRECISION NOT NULL,
    net_pnl DOUBLE PRECISION NOT NULL,

    commission DOUBLE PRECISION NOT NULL DEFAULT 0,

    horizon TEXT,
    strategy TEXT,
    regime TEXT,

    hold_seconds DOUBLE PRECISION,

    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_closed_trades_signal_id
ON closed_trades(signal_id);

CREATE INDEX IF NOT EXISTS idx_closed_trades_symbol_created_at
ON closed_trades(symbol, created_at DESC);
SQL

echo "OK: signal analytics tables created"
