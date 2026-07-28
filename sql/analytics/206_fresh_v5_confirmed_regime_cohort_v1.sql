BEGIN;

-- V4 сохраняется неизменной как аудиторская когорта старого классификатора.
-- V5 принимает только future-only сделки, созданные после включения V3.
INSERT INTO analytics.paper_portfolio_scope_v1(
    scope_code, asset_group, enabled, starts_at, source_version
)
VALUES
    ('FRESH_V5_CONFIRMED_EQUITY', 'EQUITY', true, clock_timestamp(), 'CANDLE_REGIME_V3'),
    ('FRESH_V5_CONFIRMED_FUTURES', 'FUTURES', true, clock_timestamp(), 'CANDLE_REGIME_V3')
ON CONFLICT(scope_code) DO UPDATE SET
    enabled = true,
    starts_at = excluded.starts_at,
    source_version = excluded.source_version,
    updated_at = clock_timestamp();

-- Новые Paper-позиции должны физически попадать только в V5.
UPDATE analytics.paper_portfolio_scope_v1
SET enabled = false, updated_at = clock_timestamp()
WHERE scope_code IN (
    'FRESH_V3_EQUITY', 'FRESH_V3_FUTURES',
    'FRESH_V4_REGIME_EQUITY', 'FRESH_V4_REGIME_FUTURES'
);

-- Политика направления симметрична: LONG запрещён при снижении,
-- SHORT запрещён при росте. Контртренд возможен только отдельной политикой.
UPDATE analytics.regime_strategy_routing_policy_v1
SET allowed_side = CASE regime_trend
        WHEN 'trend_up' THEN 'BUY'
        WHEN 'trend_down' THEN 'SELL'
        ELSE allowed_side
    END,
    countertrend_allowed = false,
    updated_at = clock_timestamp()
WHERE regime_trend IN ('trend_up', 'trend_down');

CREATE OR REPLACE VIEW analytics.closed_trades_fresh_v5_confirmed AS
SELECT *
FROM public.closed_trades
WHERE portfolio_scope IN (
        'FRESH_V5_CONFIRMED_EQUITY',
        'FRESH_V5_CONFIRMED_FUTURES'
    )
  AND payload->'context'->>'cohort' = portfolio_scope
  AND payload->'context'->>'regime_source_version' = 'CANDLE_REGIME_V3'
  AND COALESCE((payload->'context'->>'regime_confirmed_bars')::integer, 0) >= 3
  AND payload->'context'->>'regime_trend' IN ('trend_up', 'trend_down', 'range')
  AND payload->'context'->>'regime_vol' IN ('low_vol', 'normal_vol', 'high_vol')
  AND (
      payload->'context'->>'regime_trend' = 'range'
      OR (
          payload->'context'->>'regime_trend' = 'trend_up'
          AND upper(COALESCE(payload->'context'->>'side', payload->>'side', '')) = 'BUY'
      )
      OR (
          payload->'context'->>'regime_trend' = 'trend_down'
          AND upper(COALESCE(payload->'context'->>'side', payload->>'side', '')) = 'SELL'
      )
  );

DO $$
DECLARE item record;
BEGIN
    FOR item IN
        SELECT conname
        FROM pg_constraint
        WHERE conrelid = 'analytics.hierarchical_evidence_v1'::regclass
          AND contype = 'c'
          AND pg_get_constraintdef(oid) ILIKE '%cohort_code%'
    LOOP
        EXECUTE format(
            'ALTER TABLE analytics.hierarchical_evidence_v1 DROP CONSTRAINT %I',
            item.conname
        );
    END LOOP;
END $$;

ALTER TABLE analytics.hierarchical_evidence_v1
    ADD CONSTRAINT hierarchical_evidence_v1_cohort_code_check
    CHECK (cohort_code IN ('FRESH_V3_BASE','FRESH_V4_CONFIRM','FRESH_V5_CONFIRM'));

CREATE OR REPLACE VIEW analytics.hierarchical_oos_readiness_v1 AS
SELECT * FROM analytics.hierarchical_evidence_v1
WHERE cohort_code='FRESH_V5_CONFIRM' AND level_code='EXACT_CONTEXT';

COMMENT ON VIEW analytics.closed_trades_fresh_v5_confirmed IS
'Чистая future-only когорта V5: подтверждённый свечной режим V3, без противотрендовых сделок; V4 не смешивается.';

COMMIT;
