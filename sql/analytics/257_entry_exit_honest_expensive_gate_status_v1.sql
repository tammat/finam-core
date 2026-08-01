BEGIN;

ALTER TABLE analytics.entry_exit_promotion_workflow_v1
 DROP CONSTRAINT entry_exit_promotion_workflow_v1_workflow_stage_check;

ALTER TABLE analytics.entry_exit_promotion_workflow_v1
 ADD CONSTRAINT entry_exit_promotion_workflow_v1_workflow_stage_check
 CHECK(workflow_stage IN(
  'SHADOW_ACCUMULATION','EXPENSIVE_GATES_PENDING','EXPENSIVE_GATES_FAILED',
  'V5_OOS_COLLECTING','V5_OOS_FAILED','V5_OOS_PASS','PAPER_MINIMAL_ACTIVE',
  'PAPER_MONITOR','PAPER_CONTINUE','ROLLED_BACK','REJECTED'));

COMMENT ON COLUMN analytics.entry_exit_promotion_workflow_v1.workflow_stage IS
 'Honest fail-closed stage: FAILED means evaluated and rejected; PENDING is reserved for checks not yet completed.';

COMMIT;
