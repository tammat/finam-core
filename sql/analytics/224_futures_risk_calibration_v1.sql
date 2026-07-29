CREATE TABLE IF NOT EXISTS analytics.futures_risk_calibration_v1 (
    calibration_date date NOT NULL,
    asset_code text NOT NULL,
    side_code text NOT NULL,
    timeframe_code text NOT NULL,
    trades integer NOT NULL,
    winners integer NOT NULL,
    mae_q80_atr numeric,
    mfe_q70_atr numeric,
    current_stop_atr numeric NOT NULL,
    current_take_atr numeric NOT NULL,
    current_volume_ratio numeric NOT NULL,
    recommended_stop_atr numeric,
    recommended_take_atr numeric,
    recommended_volume_ratio numeric,
    recommendation_status text NOT NULL,
    reason_code text NOT NULL,
    payload jsonb NOT NULL DEFAULT '{}'::jsonb,
    generated_at timestamptz NOT NULL DEFAULT clock_timestamp(),
    PRIMARY KEY (calibration_date, asset_code, side_code)
);

CREATE INDEX IF NOT EXISTS futures_risk_calibration_latest_v1_idx
    ON analytics.futures_risk_calibration_v1 (asset_code, side_code, generated_at DESC);

GRANT SELECT ON analytics.futures_risk_calibration_v1 TO finam;
