CREATE TABLE IF NOT EXISTS analytics.btc_regime_shadow_v1 (
    observed_at timestamptz PRIMARY KEY,
    source_symbol text NOT NULL DEFAULT 'BTCUSD',
    source_timeframe text NOT NULL DEFAULT 'M5',
    source_bar_ts timestamptz NOT NULL,
    return_15m numeric,
    return_1h numeric,
    return_24h numeric,
    realized_vol_1h numeric,
    regime_code text NOT NULL,
    weekend_context boolean NOT NULL,
    shadow_only boolean NOT NULL DEFAULT true CHECK (shadow_only),
    source_version text NOT NULL DEFAULT 'BTC_REGIME_SHADOW_V1',
    created_at timestamptz NOT NULL DEFAULT clock_timestamp()
);

CREATE INDEX IF NOT EXISTS btc_regime_shadow_v1_source_bar_idx
    ON analytics.btc_regime_shadow_v1(source_bar_ts DESC);

COMMENT ON TABLE analytics.btc_regime_shadow_v1 IS
    'Диагностический BTC-контекст risk-on/risk-off; не участвует в Paper, V5 admission или sizing.';
