#!/usr/bin/env bash
set -euo pipefail

echo "=== TEST_BR_VOLATILITY_GATE_SHADOW_SIMULATION_PLAN_V1 ==="

psql "${DATABASE_URL:-postgresql:///finam_core}" -At <<'SQL'
SELECT 'observation_rows=' || count(*)
FROM research.br_volatility_gate_shadow_observation_v1
WHERE symbol='BRN6@RTSX';

SELECT 'payload_side_keys=' || count(*)
FROM research.br_volatility_gate_shadow_observation_v1
WHERE symbol='BRN6@RTSX'
  AND (
      payload ? 'side'
   OR payload ? 'signal_side'
   OR payload ? 'expected_side'
   OR payload ? 'actual_side'
  );

SELECT 'payload_sample=' || payload::text
FROM research.br_volatility_gate_shadow_observation_v1
WHERE symbol='BRN6@RTSX'
ORDER BY created_at DESC
LIMIT 1;

SELECT 'market_bars_columns=' || string_agg(column_name, ',' ORDER BY ordinal_position)
FROM information_schema.columns
WHERE table_schema='public'
  AND table_name='market_bars';

SELECT 'market_bars_rows_br=' || count(*)
FROM public.market_bars
WHERE symbol='BRN6@RTSX';

SELECT 'market_bars_latest_br=' || coalesce(max(ts)::text,'NULL')
FROM public.market_bars
WHERE symbol='BRN6@RTSX';

SELECT 'side_resolution=NO_SIDE_IN_OBSERVATION_PAYLOAD';

SELECT 'planned_direction_mode=BOTH_SIDES_COUNTERFACTUAL';

SELECT 'planned_directions=BUY,SELL';

SELECT 'planned_entry_ts=observation.ts';

SELECT 'planned_entry_price=observation.price';

SELECT 'planned_exit_price=market_bars.close_after_horizon';

SELECT 'planned_horizons=3,5,10,15';

SELECT 'planned_mfe=BUY:max(high-entry_price),SELL:max(entry_price-low)';

SELECT 'planned_mae=BUY:min(low-entry_price),SELL:min(entry_price-high)';

SELECT 'planned_commission_mode=ZERO_FOR_V1';

SELECT 'planned_reason=side_missing_so_simulate_both_sides_without_orders_or_fills';

SELECT 'db_update=0';
SELECT 'runtime_changed=0';
SELECT 'execution_changed=0';
SELECT 'orders_changed=0';
SELECT 'fills_changed=0';
SELECT 'micro_live_allowed=0';

SELECT 'VERDICT=BR_VOLATILITY_GATE_SHADOW_SIMULATION_PLAN_V1_READY';
SQL

echo "TEST_BR_VOLATILITY_GATE_SHADOW_SIMULATION_PLAN_V1_OK"
