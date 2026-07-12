CREATE TABLE IF NOT EXISTS analytics.relationship_data_quality_gate_v1 (
    id BIGSERIAL PRIMARY KEY,
    audit_run_id UUID NOT NULL,
    symbol TEXT NOT NULL,
    timeframe TEXT NOT NULL,
    bars INTEGER NOT NULL,
    trading_days INTEGER NOT NULL,
    first_ts TIMESTAMPTZ,
    last_ts TIMESTAMPTZ,
    latest_age_hours NUMERIC,
    duplicate_rows INTEGER NOT NULL,
    invalid_ohlc_rows INTEGER NOT NULL,
    regime_rows INTEGER NOT NULL,
    regime_coverage_ratio NUMERIC NOT NULL,
    calendar_gap_status TEXT NOT NULL CHECK(calendar_gap_status IN ('UNVERIFIED','VERIFIED')),
    market_data_status TEXT NOT NULL CHECK(market_data_status IN ('READY','DEGRADED','BLOCKED')),
    factory_status TEXT NOT NULL CHECK(factory_status IN ('READY','BLOCKED')),
    reason_codes JSONB NOT NULL,
    source_version TEXT NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE(audit_run_id,symbol,timeframe)
);

CREATE INDEX IF NOT EXISTS relationship_data_quality_gate_v1_latest_idx
    ON analytics.relationship_data_quality_gate_v1(created_at DESC,symbol,timeframe);
