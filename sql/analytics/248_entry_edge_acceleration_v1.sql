ALTER TABLE analytics.entry_exit_signal_shadow_pair_v2
  ADD COLUMN IF NOT EXISTS placebo_net_r numeric;

CREATE TABLE IF NOT EXISTS analytics.entry_exit_family_evidence_v1 (
  family_code text NOT NULL,
  side_code text NOT NULL,
  candidate_code text NOT NULL,
  evidence_status text NOT NULL,
  pairs integer NOT NULL DEFAULT 0,
  oos_pairs integer NOT NULL DEFAULT 0,
  metrics jsonb NOT NULL DEFAULT '{}'::jsonb,
  generated_at timestamptz NOT NULL DEFAULT clock_timestamp(),
  PRIMARY KEY(family_code,side_code,candidate_code)
);

CREATE INDEX IF NOT EXISTS entry_exit_family_evidence_v1_status_idx
  ON analytics.entry_exit_family_evidence_v1(evidence_status,generated_at DESC);

GRANT SELECT,INSERT,UPDATE,DELETE ON analytics.entry_exit_family_evidence_v1 TO finam;
GRANT SELECT ON analytics.entry_exit_family_evidence_v1 TO alex,finam_user;

COMMENT ON COLUMN analytics.entry_exit_signal_shadow_pair_v2.placebo_net_r IS
  'Causal unconditional next-bar control using identical horizon, risk geometry and costs.';
COMMENT ON TABLE analytics.entry_exit_family_evidence_v1 IS
  'Diagnostic-only purged family evidence. It cannot authorize Paper or REAL promotion.';
