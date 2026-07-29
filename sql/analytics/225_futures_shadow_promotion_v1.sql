CREATE TABLE IF NOT EXISTS analytics.futures_risk_shadow_pair_v1 (
  trade_id bigint NOT NULL, asset_code text NOT NULL, side_code text NOT NULL,
  candidate_version text NOT NULL, entry_ts timestamptz NOT NULL, exit_ts timestamptz NOT NULL,
  actual_net_r numeric NOT NULL, shadow_net_r numeric NOT NULL,
  shadow_exit_reason text NOT NULL, shadow_exit_price numeric NOT NULL,
  stop_atr numeric NOT NULL, take_atr numeric NOT NULL, is_oos boolean NOT NULL DEFAULT false,
  generated_at timestamptz NOT NULL DEFAULT clock_timestamp(),
  PRIMARY KEY (trade_id,candidate_version)
);

CREATE TABLE IF NOT EXISTS analytics.futures_risk_runtime_profile_v1 (
  asset_code text NOT NULL, side_code text NOT NULL, execution_mode text NOT NULL DEFAULT 'paper',
  version integer NOT NULL, status text NOT NULL, mode text NOT NULL,
  min_stop_atr numeric NOT NULL, max_stop_atr numeric NOT NULL, target_atr numeric NOT NULL,
  min_reward_r numeric NOT NULL, min_volume_ratio numeric NOT NULL,
  source_calibration_date date NOT NULL, promotion_metrics jsonb NOT NULL,
  previous_profile jsonb, activated_at timestamptz, created_at timestamptz NOT NULL DEFAULT clock_timestamp(),
  PRIMARY KEY(asset_code,side_code,execution_mode,version)
);
CREATE UNIQUE INDEX IF NOT EXISTS futures_risk_one_active_profile_v1_idx
ON analytics.futures_risk_runtime_profile_v1(asset_code,side_code,execution_mode) WHERE status='ACTIVE';
GRANT SELECT ON analytics.futures_risk_shadow_pair_v1,analytics.futures_risk_runtime_profile_v1 TO finam;
