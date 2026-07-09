CREATE TABLE IF NOT EXISTS knowledge.trading_plan_parameter_profile_v1 (
    profile_code            TEXT PRIMARY KEY,
    profile_name            TEXT NOT NULL,
    entry_source            TEXT NOT NULL,
    stop_source             TEXT NOT NULL,
    target_source           TEXT NOT NULL,
    trailing_source         TEXT NOT NULL,
    horizon_source          TEXT NOT NULL,
    risk_model              TEXT NOT NULL,
    enabled                 BOOLEAN NOT NULL DEFAULT TRUE,
    source_version          TEXT NOT NULL,
    created_at              TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at              TIMESTAMPTZ NOT NULL DEFAULT now()
);

INSERT INTO knowledge.trading_plan_parameter_profile_v1
(
    profile_code,
    profile_name,
    entry_source,
    stop_source,
    target_source,
    trailing_source,
    horizon_source,
    risk_model,
    enabled,
    source_version
)
VALUES
(
    'PROFILE_DEFAULT',
    'Default Trading Plan',
    'BREAKOUT_LEVEL',
    'SUPPORT',
    'FIBONACCI_EXTENSION',
    'DISABLED',
    'PLATFORM_PARAMETER',
    'FIXED_RISK',
    TRUE,
    'TRADING_PLAN_PARAMETER_PROFILE_V1'
),
(
    'PROFILE_CONSERVATIVE',
    'Conservative Trading Plan',
    'SUPPORT',
    'SWING_LOW',
    'RESISTANCE',
    'DISABLED',
    'PLATFORM_PARAMETER',
    'FIXED_RISK',
    TRUE,
    'TRADING_PLAN_PARAMETER_PROFILE_V1'
),
(
    'PROFILE_MOMENTUM',
    'Momentum Trading Plan',
    'BREAKOUT_LEVEL',
    'ATR',
    'RR',
    'ATR',
    'PLATFORM_PARAMETER',
    'VOLATILITY',
    TRUE,
    'TRADING_PLAN_PARAMETER_PROFILE_V1'
)
ON CONFLICT(profile_code)
DO UPDATE SET
    profile_name     = EXCLUDED.profile_name,
    entry_source     = EXCLUDED.entry_source,
    stop_source      = EXCLUDED.stop_source,
    target_source    = EXCLUDED.target_source,
    trailing_source  = EXCLUDED.trailing_source,
    horizon_source   = EXCLUDED.horizon_source,
    risk_model       = EXCLUDED.risk_model,
    enabled          = EXCLUDED.enabled,
    source_version   = EXCLUDED.source_version,
    updated_at       = now();
