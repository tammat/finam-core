BEGIN;

ALTER TABLE analytics.v5_post_fix_branch_registry_v1
  DROP CONSTRAINT IF EXISTS v5_post_fix_branch_registry_v1_state_code_check;
UPDATE analytics.v5_post_fix_branch_registry_v1
SET state_code='PROSPECTIVE_ACCUMULATING'
WHERE state_code='FROZEN_COLLECTING';
ALTER TABLE analytics.v5_post_fix_branch_registry_v1
  ADD CONSTRAINT v5_post_fix_branch_registry_v1_state_code_check CHECK(state_code IN (
    'PROSPECTIVE_ACCUMULATING','READY_FOR_V5','V5_COLLECTING','OOS_PASS','OOS_FAIL','EARLY_REJECT','RETIRED'
  ));

CREATE TABLE IF NOT EXISTS analytics.prospective_shadow_funnel_v1 (
  branch_code text NOT NULL REFERENCES analytics.v5_post_fix_branch_registry_v1(branch_code),
  evaluated_at timestamptz NOT NULL,
  source_opportunities integer NOT NULL,
  candidate_evaluated integer NOT NULL,
  entry_eligible integer NOT NULL,
  shadow_entered integer NOT NULL,
  shadow_closed integer NOT NULL,
  independent_closed integer NOT NULL,
  profitable_closed integer NOT NULL,
  dominant_block_reason text,
  dominant_block_count integer NOT NULL DEFAULT 0,
  PRIMARY KEY(branch_code,evaluated_at)
);

CREATE TABLE IF NOT EXISTS analytics.prospective_shadow_gate_decision_v1 (
  branch_code text NOT NULL REFERENCES analytics.v5_post_fix_branch_registry_v1(branch_code),
  evaluated_at timestamptz NOT NULL,
  decision_code text NOT NULL CHECK(decision_code IN ('ACCUMULATING','READY_FOR_V5','EARLY_REJECT')),
  reason_code text NOT NULL,
  independent_observations integer NOT NULL,
  trading_days integer NOT NULL,
  expectancy_r numeric,
  profit_factor numeric,
  top_gain_share numeric,
  oos_admission_id uuid,
  metrics jsonb NOT NULL DEFAULT '{}'::jsonb,
  PRIMARY KEY(branch_code,evaluated_at)
);

CREATE OR REPLACE VIEW analytics.prospective_shadow_gate_latest_v1 AS
SELECT DISTINCT ON(branch_code) *
FROM analytics.prospective_shadow_gate_decision_v1
ORDER BY branch_code,evaluated_at DESC;

GRANT SELECT,INSERT ON analytics.prospective_shadow_funnel_v1 TO alex,finam;
GRANT SELECT,INSERT ON analytics.prospective_shadow_gate_decision_v1 TO alex,finam;
GRANT SELECT ON analytics.prospective_shadow_gate_latest_v1 TO alex,finam;

COMMIT;
