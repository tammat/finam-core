BEGIN;

CREATE TABLE IF NOT EXISTS analytics.entry_exit_promotion_workflow_v1(
 strategy_code text NOT NULL,
 symbol_group text NOT NULL,
 side_code text NOT NULL,
 candidate_code text NOT NULL,
 workflow_stage text NOT NULL CHECK(workflow_stage IN(
  'SHADOW_ACCUMULATION','EXPENSIVE_GATES_PENDING','V5_OOS_COLLECTING',
  'V5_OOS_FAILED','V5_OOS_PASS','PAPER_MINIMAL_ACTIVE','PAPER_MONITOR',
  'PAPER_CONTINUE','ROLLED_BACK','REJECTED')),
 statistical_verdict text NOT NULL CHECK(statistical_verdict IN('ACCUMULATE','PASS','FAIL')),
 expensive_gates_pass boolean NOT NULL DEFAULT false,
 v5_oos_pass boolean NOT NULL DEFAULT false,
 paper_risk_fraction numeric NOT NULL DEFAULT .25
   CHECK(paper_risk_fraction > 0 AND paper_risk_fraction <= .25),
 evidence jsonb NOT NULL DEFAULT '{}'::jsonb,
 first_entered_at timestamptz NOT NULL DEFAULT clock_timestamp(),
 last_transition_at timestamptz NOT NULL DEFAULT clock_timestamp(),
 updated_at timestamptz NOT NULL DEFAULT clock_timestamp(),
 PRIMARY KEY(strategy_code,symbol_group,side_code,candidate_code)
);

CREATE INDEX IF NOT EXISTS entry_exit_promotion_workflow_stage_v1_idx
 ON analytics.entry_exit_promotion_workflow_v1(workflow_stage,updated_at DESC);

COMMENT ON TABLE analytics.entry_exit_promotion_workflow_v1 IS
 'Fail-closed Paper-only chain: paired statistical PASS, expensive guards, purged V5 OOS, minimal Paper observation and rollback. Never enables REAL.';

GRANT SELECT,INSERT,UPDATE ON analytics.entry_exit_promotion_workflow_v1 TO alex;

COMMIT;
