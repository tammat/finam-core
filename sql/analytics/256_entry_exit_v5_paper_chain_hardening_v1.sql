BEGIN;

ALTER TABLE analytics.entry_exit_promotion_workflow_v1
 ADD COLUMN IF NOT EXISTS admission_id uuid REFERENCES analytics.trade_outcome_oos_admission_v1(admission_id),
 ADD COLUMN IF NOT EXISTS oos_run_id uuid REFERENCES analytics.v5_oos_run_v1(run_id);

CREATE UNIQUE INDEX IF NOT EXISTS entry_exit_workflow_admission_v1_uidx
 ON analytics.entry_exit_promotion_workflow_v1(admission_id) WHERE admission_id IS NOT NULL;

GRANT SELECT,INSERT,UPDATE ON analytics.entry_exit_promotion_workflow_v1 TO alex;

COMMIT;
