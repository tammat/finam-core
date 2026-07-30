CREATE TABLE IF NOT EXISTS analytics.entry_exit_champion_challenger_v1 (
  strategy_code text NOT NULL,
  symbol_group text NOT NULL,
  side_code text NOT NULL,
  champion_profile_id bigint REFERENCES analytics.entry_exit_runtime_profile_v1(profile_id),
  champion_candidate_code text NOT NULL DEFAULT 'CURRENT_PAPER',
  challenger_candidate_code text,
  challenger_status text NOT NULL CHECK (challenger_status IN (
    'SHADOW_ACCUMULATION','PAPER_CHALLENGER','KEEP_PAPER_CHALLENGER',
    'READY_FOR_CHAMPION_CONFIRMATION','CHAMPION_ACTIVE','ROLLED_BACK','REJECTED'
  )),
  challenger_selected_at timestamptz,
  shadow_metrics jsonb NOT NULL DEFAULT '{}'::jsonb,
  paper_metrics jsonb NOT NULL DEFAULT '{}'::jsonb,
  auto_selected boolean NOT NULL DEFAULT false,
  updated_at timestamptz NOT NULL DEFAULT clock_timestamp(),
  PRIMARY KEY(strategy_code,symbol_group,side_code)
);

CREATE INDEX IF NOT EXISTS entry_exit_challenger_status_v1_idx
ON analytics.entry_exit_champion_challenger_v1(challenger_status,updated_at DESC);

GRANT SELECT,INSERT,UPDATE ON analytics.entry_exit_champion_challenger_v1 TO finam;
GRANT SELECT ON analytics.entry_exit_champion_challenger_v1 TO alex,finam_user;
