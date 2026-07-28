-- One cumulative counter per exact FRESH_V2 execution scope.
ALTER TABLE analytics.trade_outcome_hypothesis_v1
    DROP CONSTRAINT IF EXISTS trade_outcome_hypothesis_v1_lifecycle_state_check;

ALTER TABLE analytics.trade_outcome_hypothesis_v1
    ADD CONSTRAINT trade_outcome_hypothesis_v1_lifecycle_state_check
    CHECK (lifecycle_state IN (
        'GENERATED','WAITING_FRESH_DATA','READY_FOR_OOS',
        'WAITING_CONTEXT','RESTRICTED','CLOSED'
    ));

-- Preserve the legacy evidence for audit, but remove it from the active queue.
UPDATE analytics.trade_outcome_oos_admission_v1 a
SET status_code='CLOSED',reason_code='SUPERSEDED_BY_FRESH_V2_FULL_SCOPE',
    updated_at=clock_timestamp()
FROM analytics.trade_outcome_hypothesis_v1 h
WHERE h.hypothesis_id=a.hypothesis_id
  AND coalesce(h.evidence->>'scope','') <> 'FULL_SCOPE'
  AND a.status_code <> 'CLOSED';

UPDATE analytics.trade_outcome_hypothesis_v1
SET lifecycle_state='CLOSED',recommendation_code='SUPERSEDED_BY_FRESH_V2_FULL_SCOPE',
    updated_at=clock_timestamp()
WHERE coalesce(evidence->>'scope','') <> 'FULL_SCOPE'
  AND lifecycle_state <> 'CLOSED';

UPDATE analytics.system_job_schedule_v1
SET interval_minutes=2,priority=8,updated_at=clock_timestamp()
WHERE job_code='TRADE_OUTCOME_HYPOTHESIS_GENERATOR';

UPDATE analytics.system_job_schedule_v1
SET interval_minutes=2,priority=9,updated_at=clock_timestamp()
WHERE job_code='TRADE_OUTCOME_OOS_ADMISSION';

GRANT SELECT,INSERT,UPDATE ON analytics.trade_outcome_hypothesis_v1 TO finam;
GRANT SELECT,INSERT,UPDATE ON analytics.trade_outcome_oos_admission_v1 TO finam;
