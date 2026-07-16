BEGIN;
ALTER TABLE analytics.operator_decision_workspace_v2 ADD COLUMN IF NOT EXISTS baseline_value NUMERIC;
ALTER TABLE analytics.operator_decision_workspace_v2 ADD COLUMN IF NOT EXISTS measurement_due_at TIMESTAMPTZ;
ALTER TABLE analytics.operator_decision_workspace_v2 ADD COLUMN IF NOT EXISTS measured_at TIMESTAMPTZ;
ALTER TABLE analytics.operator_decision_workspace_v2 ADD COLUMN IF NOT EXISTS measurement_source_identity TEXT;
ALTER TABLE analytics.operator_decision_workspace_v2 DROP CONSTRAINT IF EXISTS operator_decision_feedback_consistency_v2;
ALTER TABLE analytics.operator_decision_workspace_v2 ADD CONSTRAINT operator_decision_feedback_consistency_v2 CHECK (
    (feedback_status='PENDING' AND actual_result IS NULL AND measured_at IS NULL)
    OR (feedback_status='MEASURED' AND actual_result IS NOT NULL AND measured_at IS NOT NULL AND measurement_source_identity IS NOT NULL)
    OR (feedback_status='NOT_APPLICABLE' AND actual_result IS NULL)
) NOT VALID;
ALTER TABLE analytics.operator_decision_workspace_v2 VALIDATE CONSTRAINT operator_decision_feedback_consistency_v2;
COMMIT;
