ALTER TABLE analytics.entry_exit_champion_challenger_v1
  ADD COLUMN IF NOT EXISTS champion_metrics jsonb NOT NULL DEFAULT '{}'::jsonb,
  ADD COLUMN IF NOT EXISTS consecutive_degraded_cycles integer NOT NULL DEFAULT 0,
  ADD COLUMN IF NOT EXISTS rollback_reason text,
  ADD COLUMN IF NOT EXISTS last_transition_at timestamptz;

COMMENT ON COLUMN analytics.entry_exit_champion_challenger_v1.consecutive_degraded_cycles IS
  'Paper-only soft degradation counter; two consecutive daily cycles trigger rollback.';

GRANT SELECT,INSERT,UPDATE ON analytics.entry_exit_champion_challenger_v1 TO finam;
