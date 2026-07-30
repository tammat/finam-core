CREATE TABLE IF NOT EXISTS analytics.entry_exit_signal_shadow_pair_v2 (
  source_signal_id bigint NOT NULL REFERENCES signals(id),
  signal_id text NOT NULL,
  incumbent_trade_id bigint,
  source_status text NOT NULL,
  strategy_code text NOT NULL,
  symbol_code text NOT NULL,
  side_code text NOT NULL,
  candidate_code text NOT NULL,
  entry_mode text NOT NULL,
  stop_atr numeric NOT NULL,
  take_atr numeric NOT NULL,
  actual_net_r numeric NOT NULL,
  shadow_entered boolean NOT NULL,
  shadow_net_r numeric,
  shadow_exit_reason text NOT NULL,
  entry_decision text NOT NULL,
  entry_decision_reason text NOT NULL,
  entry_context jsonb NOT NULL,
  label_start_ts timestamptz NOT NULL,
  label_end_ts timestamptz NOT NULL,
  is_oos boolean NOT NULL DEFAULT false,
  generated_at timestamptz NOT NULL DEFAULT clock_timestamp(),
  PRIMARY KEY(source_signal_id,candidate_code)
);

CREATE INDEX IF NOT EXISTS entry_exit_signal_shadow_pair_v2_oos_idx
ON analytics.entry_exit_signal_shadow_pair_v2(strategy_code,symbol_code,side_code,is_oos,label_start_ts);

GRANT SELECT,INSERT,UPDATE,DELETE ON analytics.entry_exit_signal_shadow_pair_v2 TO finam;
GRANT SELECT ON analytics.entry_exit_signal_shadow_pair_v2 TO alex,finam_user;

COMMENT ON TABLE analytics.entry_exit_signal_shadow_pair_v2 IS
  'Полный V5 signal funnel: причинно симулированный incumbent и Shadow на одинаковых сигналах, включая отклонённые Paper.';
