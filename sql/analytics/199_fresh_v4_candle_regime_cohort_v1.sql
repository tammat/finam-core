BEGIN;

-- Новая когорта начинается только после включения свечного режима V2.
-- FRESH_V3 не изменяется и остаётся историческим основанием для сравнения.
INSERT INTO analytics.paper_portfolio_scope_v1(
    scope_code, asset_group, enabled, starts_at, source_version
)
VALUES
    ('FRESH_V4_REGIME_EQUITY', 'EQUITY', true, clock_timestamp(), 'CANDLE_REGIME_V2'),
    ('FRESH_V4_REGIME_FUTURES', 'FUTURES', true, clock_timestamp(), 'CANDLE_REGIME_V2')
ON CONFLICT(scope_code) DO UPDATE SET
    enabled = true,
    starts_at = excluded.starts_at,
    source_version = excluded.source_version,
    updated_at = clock_timestamp();

CREATE OR REPLACE VIEW analytics.closed_trades_fresh_v4_regime AS
SELECT *
FROM public.closed_trades
WHERE portfolio_scope IN ('FRESH_V4_REGIME_EQUITY','FRESH_V4_REGIME_FUTURES')
  AND payload->'context'->>'cohort' = portfolio_scope
  AND payload->'context'->>'regime_source_version' = 'CANDLE_REGIME_V2';

COMMENT ON VIEW analytics.closed_trades_fresh_v4_regime IS
'Чистая future-only когорта свечного режима V2; не смешивается с 85 сделками FRESH_V3.';

COMMIT;
