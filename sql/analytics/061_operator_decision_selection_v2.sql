BEGIN;
ALTER TABLE marketcore_action.command_request_v2 ADD COLUMN IF NOT EXISTS target_id TEXT;
ALTER TABLE analytics.operator_decision_workspace_v2 ADD COLUMN IF NOT EXISTS selection_status TEXT NOT NULL DEFAULT 'NOT_SELECTED' CHECK (selection_status IN ('NOT_SELECTED','ACKNOWLEDGED'));
ALTER TABLE analytics.operator_decision_workspace_v2 ADD COLUMN IF NOT EXISTS selected_at TIMESTAMPTZ;
ALTER TABLE analytics.operator_decision_workspace_v2 ADD COLUMN IF NOT EXISTS selected_by TEXT;
DO $$ BEGIN
IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname='operator_decision_selection_consistency_v2') THEN
    ALTER TABLE analytics.operator_decision_workspace_v2 ADD CONSTRAINT operator_decision_selection_consistency_v2 CHECK (
        (selection_status='NOT_SELECTED' AND selected_at IS NULL AND selected_by IS NULL)
        OR (selection_status='ACKNOWLEDGED' AND selected_at IS NOT NULL AND selected_by IS NOT NULL)
    ) NOT VALID;
END IF;
END $$;
ALTER TABLE analytics.operator_decision_workspace_v2 VALIDATE CONSTRAINT operator_decision_selection_consistency_v2;
COMMIT;
