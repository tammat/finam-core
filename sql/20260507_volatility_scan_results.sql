CREATE TABLE IF NOT EXISTS volatility_scan_results (
    id BIGSERIAL PRIMARY KEY,
    scan_ts TIMESTAMPTZ NOT NULL DEFAULT now(),
    timeframe TEXT NOT NULL,
    bucket TEXT NOT NULL,
    rank INTEGER NOT NULL,
    symbol TEXT NOT NULL,
    score DOUBLE PRECISION,
    atr_pct DOUBLE PRECISION,
    turnover DOUBLE PRECISION,
    volume DOUBLE PRECISION,
    avg_volume DOUBLE PRECISION,
    raw_json JSONB NOT NULL DEFAULT '{}'::jsonb
);

CREATE INDEX IF NOT EXISTS idx_volatility_scan_results_scan_ts
    ON volatility_scan_results (scan_ts DESC);

CREATE INDEX IF NOT EXISTS idx_volatility_scan_results_symbol_scan_ts
    ON volatility_scan_results (symbol, scan_ts DESC);

CREATE INDEX IF NOT EXISTS idx_volatility_scan_results_bucket_scan_ts
    ON volatility_scan_results (bucket, scan_ts DESC);
