CREATE TABLE IF NOT EXISTS analytics.entry_exit_pending_entry_v1 (
  pending_id bigserial PRIMARY KEY,
  profile_id bigint NOT NULL REFERENCES analytics.entry_exit_runtime_profile_v1(profile_id),
  candidate_code text NOT NULL,
  strategy_code text NOT NULL,
  symbol_group text NOT NULL,
  symbol_code text NOT NULL,
  side_code text NOT NULL,
  entry_mode text NOT NULL CHECK(entry_mode IN ('IMMEDIATE','CONFIRM_1','RETEST_3','SKIP')),
  signal_id text NOT NULL,
  signal_ts timestamptz NOT NULL,
  signal_price numeric NOT NULL,
  atr numeric NOT NULL,
  timeframe text NOT NULL CHECK(timeframe IN ('M1','M5')),
  entry_context jsonb NOT NULL,
  intent_payload jsonb NOT NULL,
  status text NOT NULL CHECK(status IN ('PENDING','READY','CONSUMED','SKIPPED','CANCELLED','EXPIRED')),
  decision_reason text NOT NULL,
  resolved_entry_price numeric,
  resolved_at timestamptz,
  created_at timestamptz NOT NULL DEFAULT clock_timestamp(),
  updated_at timestamptz NOT NULL DEFAULT clock_timestamp()
);

CREATE UNIQUE INDEX IF NOT EXISTS entry_exit_one_pending_entry_v1_idx
ON analytics.entry_exit_pending_entry_v1(profile_id,symbol_code,side_code)
WHERE status IN ('PENDING','READY');

CREATE INDEX IF NOT EXISTS entry_exit_pending_worker_v1_idx
ON analytics.entry_exit_pending_entry_v1(status,signal_ts);

GRANT SELECT,INSERT,UPDATE ON analytics.entry_exit_pending_entry_v1 TO finam,alex;
GRANT SELECT ON analytics.entry_exit_pending_entry_v1 TO finam_user;
GRANT USAGE,SELECT ON SEQUENCE analytics.entry_exit_pending_entry_v1_pending_id_seq TO finam,alex;

COMMENT ON TABLE analytics.entry_exit_pending_entry_v1 IS
  'Персистентное Paper-ожидание CONFIRM_1/RETEST_3; REAL не обслуживается.';
