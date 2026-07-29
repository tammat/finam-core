CREATE TABLE IF NOT EXISTS analytics.entry_exit_runtime_profile_v1 (
  profile_id bigserial PRIMARY KEY,
  strategy_code text NOT NULL,
  symbol_group text NOT NULL,
  side_code text NOT NULL,
  candidate_code text NOT NULL,
  execution_mode text NOT NULL DEFAULT 'paper' CHECK(execution_mode='paper'),
  status text NOT NULL CHECK(status IN ('ACTIVE','SUPERSEDED','ROLLED_BACK')),
  entry_mode text NOT NULL,
  stop_atr numeric NOT NULL,
  take_atr numeric NOT NULL,
  trail_after_r numeric,
  trail_atr numeric,
  source_metrics jsonb NOT NULL,
  activated_by text NOT NULL,
  activated_at timestamptz NOT NULL DEFAULT clock_timestamp(),
  deactivated_at timestamptz,
  rollback_of_profile_id bigint REFERENCES analytics.entry_exit_runtime_profile_v1(profile_id)
);
CREATE UNIQUE INDEX IF NOT EXISTS entry_exit_one_active_profile_v1_idx
ON analytics.entry_exit_runtime_profile_v1(strategy_code,symbol_group,side_code,execution_mode)
WHERE status='ACTIVE';

CREATE TABLE IF NOT EXISTS analytics.entry_exit_operator_decision_v1 (
  decision_id bigserial PRIMARY KEY,
  strategy_code text NOT NULL,
  symbol_group text NOT NULL,
  side_code text NOT NULL,
  candidate_code text NOT NULL,
  decision_code text NOT NULL CHECK(decision_code IN ('CONFIRM_PAPER','REJECT','CONTINUE_SHADOW','ROLLBACK')),
  actor_id text NOT NULL,
  request_id uuid NOT NULL UNIQUE,
  reason_code text NOT NULL,
  created_at timestamptz NOT NULL DEFAULT clock_timestamp()
);
GRANT SELECT ON analytics.entry_exit_runtime_profile_v1,analytics.entry_exit_operator_decision_v1 TO alex,finam,finam_user;
GRANT USAGE,SELECT ON SEQUENCE analytics.entry_exit_runtime_profile_v1_profile_id_seq,analytics.entry_exit_operator_decision_v1_decision_id_seq TO alex;
