CREATE TABLE IF NOT EXISTS analytics.entry_exit_shadow_pair_v1 (
  trade_id bigint NOT NULL,
  strategy_code text NOT NULL,
  symbol_code text NOT NULL,
  side_code text NOT NULL,
  candidate_code text NOT NULL,
  entry_mode text NOT NULL,
  stop_atr numeric NOT NULL,
  take_atr numeric NOT NULL,
  trail_after_r numeric,
  trail_atr numeric,
  actual_net_r numeric NOT NULL,
  shadow_entered boolean NOT NULL,
  shadow_net_r numeric,
  shadow_exit_reason text NOT NULL,
  is_oos boolean NOT NULL DEFAULT false,
  generated_at timestamptz NOT NULL DEFAULT clock_timestamp(),
  PRIMARY KEY (trade_id,candidate_code)
);

CREATE TABLE IF NOT EXISTS analytics.entry_exit_recommendation_v1 (
  strategy_code text NOT NULL,
  symbol_group text NOT NULL,
  side_code text NOT NULL,
  candidate_code text NOT NULL,
  recommendation_status text NOT NULL,
  pairs integer NOT NULL,
  oos_pairs integer NOT NULL DEFAULT 0,
  entry_mode text NOT NULL,
  stop_atr numeric NOT NULL,
  take_atr numeric NOT NULL,
  trail_after_r numeric,
  trail_atr numeric,
  metrics jsonb NOT NULL DEFAULT '{}'::jsonb,
  operator_decision text,
  operator_decided_at timestamptz,
  generated_at timestamptz NOT NULL DEFAULT clock_timestamp(),
  PRIMARY KEY(strategy_code,symbol_group,side_code,candidate_code)
);

CREATE INDEX IF NOT EXISTS entry_exit_recommendation_status_v1_idx
ON analytics.entry_exit_recommendation_v1(recommendation_status,generated_at DESC);
GRANT SELECT ON analytics.entry_exit_shadow_pair_v1,analytics.entry_exit_recommendation_v1 TO finam;
