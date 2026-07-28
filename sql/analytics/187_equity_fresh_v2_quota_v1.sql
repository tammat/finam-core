BEGIN;

-- Исследовательские Paper-сделки акций получают собственную квоту. Она
-- применяется отдельно к каждому каноническому ключу
-- symbol x strategy x regime; портфельные и runtime-риск-проверки сохраняются.
INSERT INTO analytics.paper_research_quota_policy_v1(
    policy_code, enabled, execution_mode, normalized_symbol, strategy,
    regime_code, window_seconds, max_fills, reservation_ttl_seconds,
    priority, reserved_research_slots, config_version, updated_at
)
VALUES (
    'EQUITY_RESEARCH_PAPER_V1', true, 'PAPER', '*',
    'VOLATILITY_BREAKOUT_EQUITY', 'ANY', 3600, 6, 180,
    10, true, '187_equity_fresh_v2_quota_v1', clock_timestamp()
)
ON CONFLICT (policy_code) DO UPDATE SET
    enabled = EXCLUDED.enabled,
    execution_mode = EXCLUDED.execution_mode,
    normalized_symbol = EXCLUDED.normalized_symbol,
    strategy = EXCLUDED.strategy,
    regime_code = EXCLUDED.regime_code,
    window_seconds = EXCLUDED.window_seconds,
    max_fills = EXCLUDED.max_fills,
    reservation_ttl_seconds = EXCLUDED.reservation_ttl_seconds,
    priority = EXCLUDED.priority,
    reserved_research_slots = EXCLUDED.reserved_research_slots,
    config_version = EXCLUDED.config_version,
    updated_at = clock_timestamp();

-- Исправляется только уже подтверждённая запись X5 новой когорты. История
-- других инструментов не переписывается.
UPDATE public.closed_trades
SET root_symbol = 'X5',
    payload = jsonb_set(payload, '{context,root_symbol}', to_jsonb('X5'::text), true)
WHERE payload->'context'->>'cohort' = 'FRESH_V2'
  AND symbol = 'X5@MISX'
  AND root_symbol = 'X';

COMMIT;
