BEGIN;

ALTER TABLE marketcore_action.action_audit_v2
    DROP CONSTRAINT IF EXISTS action_audit_v2_stage_check;
ALTER TABLE marketcore_action.action_audit_v2
    ADD CONSTRAINT action_audit_v2_stage_check CHECK (
        stage IN ('DECISION','EXECUTION_STARTED','EXECUTION_FINISHED','ROLLBACK_STARTED','ROLLBACK_FINISHED')
    );

ALTER TABLE marketcore_action.action_audit_v2
    DROP CONSTRAINT IF EXISTS action_audit_v2_status_check;
ALTER TABLE marketcore_action.action_audit_v2
    ADD CONSTRAINT action_audit_v2_status_check CHECK (
        status IN ('NAVIGATED','EXECUTED','DENIED','APPROVAL_REQUIRED','DUPLICATE','FAILED','ROLLED_BACK','ROLLBACK_FAILED')
    );

COMMIT;
