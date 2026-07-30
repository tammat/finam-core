ALTER TABLE analytics.entry_exit_shadow_pair_v1
  ADD COLUMN IF NOT EXISTS entry_decision text,
  ADD COLUMN IF NOT EXISTS entry_decision_reason text,
  ADD COLUMN IF NOT EXISTS entry_context jsonb NOT NULL DEFAULT '{}'::jsonb;

CREATE INDEX IF NOT EXISTS entry_exit_shadow_pair_adaptive_audit_v1_idx
ON analytics.entry_exit_shadow_pair_v1(entry_decision,generated_at DESC)
WHERE entry_mode='ADAPTIVE';

COMMENT ON COLUMN analytics.entry_exit_shadow_pair_v1.entry_decision IS
  'Фактический маршрут входа: IMMEDIATE, CONFIRM_1, RETEST_3 или SKIP.';
COMMENT ON COLUMN analytics.entry_exit_shadow_pair_v1.entry_decision_reason IS
  'Причина маршрута или отказа, вычисленная только из доступного до входа контекста.';
COMMENT ON COLUMN analytics.entry_exit_shadow_pair_v1.entry_context IS
  'Аудит pre-entry признаков: ATR-percentile, относительный объём, режим и издержки/ATR.';
