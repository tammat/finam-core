BEGIN;

CREATE OR REPLACE FUNCTION marketcore_action.sync_command_process_state_v1()
RETURNS trigger LANGUAGE plpgsql AS $$
DECLARE cycle_status text; cycle_reason text; mapped_status text; mapped_outcome text;
BEGIN
  IF NEW.process_id IS NULL OR NEW.status IS NOT DISTINCT FROM OLD.status THEN RETURN NEW; END IF;
  IF NEW.request_kind='EDGE_SEARCH_RUN' THEN
    SELECT c.status_code,c.reason_code INTO cycle_status,cycle_reason
    FROM marketcore_action.edge_search_request_run_v1 l
    JOIN analytics.edge_search_cycle_status_v1 c USING(cycle_id)
    WHERE l.request_id=NEW.request_id;
  END IF;
  mapped_status := CASE NEW.status
    WHEN 'PENDING' THEN 'PENDING' WHEN 'RUNNING' THEN 'RUNNING'
    WHEN 'FAILED' THEN 'FAILED' WHEN 'CANCELLED' THEN 'SKIPPED'
    WHEN 'COMPLETED' THEN CASE WHEN cycle_status='SKIPPED' THEN 'SKIPPED' ELSE 'SUCCEEDED' END
    ELSE 'FAILED' END;
  mapped_outcome := CASE
    WHEN NEW.status='CANCELLED' THEN 'CANCELLED'
    WHEN cycle_status IS NOT NULL THEN cycle_status
    ELSE NEW.status END;
  UPDATE marketcore_action.research_process_v1 SET
    status_code=mapped_status,
    progress_pct=CASE WHEN mapped_status IN ('SUCCEEDED','FAILED','SKIPPED') THEN 100 ELSE progress_pct END,
    current_step_code=CASE WHEN mapped_status IN ('SUCCEEDED','FAILED','SKIPPED') THEN 'COMPLETE' ELSE current_step_code END,
    outcome_code=CASE WHEN mapped_status IN ('SUCCEEDED','FAILED','SKIPPED') THEN mapped_outcome ELSE outcome_code END,
    reason_code=coalesce(cycle_reason,NEW.failure_code,CASE WHEN NEW.status='CANCELLED' THEN 'COMMAND_CANCELLED' END,reason_code),
    explanation_ru=CASE
      WHEN cycle_status='SKIPPED' THEN 'Системный запуск безопасно перенесён по графику или нагрузке'
      WHEN NEW.status='CANCELLED' THEN 'Заявка отменена до выполнения'
      ELSE explanation_ru END,
    finished_at=CASE WHEN mapped_status IN ('SUCCEEDED','FAILED','SKIPPED') THEN coalesce(NEW.finished_at,clock_timestamp()) ELSE finished_at END,
    updated_at=clock_timestamp()
  WHERE process_id=NEW.process_id;
  INSERT INTO marketcore_action.research_process_event_v1
    (process_id,event_code,status_code,progress_pct,step_code,payload)
  SELECT NEW.process_id,'COMMAND_STATE_SYNCED',mapped_status,
         CASE WHEN mapped_status IN ('SUCCEEDED','FAILED','SKIPPED') THEN 100 ELSE p.progress_pct END,
         p.current_step_code,jsonb_build_object('request_id',NEW.request_id,'command_status',NEW.status,
                                               'cycle_status',cycle_status)
  FROM marketcore_action.research_process_v1 p WHERE p.process_id=NEW.process_id;
  RETURN NEW;
END $$;

DROP TRIGGER IF EXISTS command_request_process_state_sync_v1 ON marketcore_action.command_request_v2;
CREATE CONSTRAINT TRIGGER command_request_process_state_sync_v1
AFTER UPDATE ON marketcore_action.command_request_v2
DEFERRABLE INITIALLY DEFERRED FOR EACH ROW
EXECUTE FUNCTION marketcore_action.sync_command_process_state_v1();

UPDATE marketcore_action.research_process_v1 p SET
 status_code=CASE q.status WHEN 'CANCELLED' THEN 'SKIPPED' WHEN 'FAILED' THEN 'FAILED'
   WHEN 'COMPLETED' THEN 'SUCCEEDED' WHEN 'RUNNING' THEN 'RUNNING' ELSE 'PENDING' END,
 progress_pct=CASE WHEN q.status IN ('CANCELLED','FAILED','COMPLETED') THEN 100 ELSE p.progress_pct END,
 current_step_code=CASE WHEN q.status IN ('CANCELLED','FAILED','COMPLETED') THEN 'COMPLETE' ELSE p.current_step_code END,
 outcome_code=CASE WHEN q.status='CANCELLED' THEN 'CANCELLED' ELSE p.outcome_code END,
 reason_code=CASE WHEN q.status='CANCELLED' THEN 'COMMAND_CANCELLED' ELSE coalesce(q.failure_code,p.reason_code) END,
 finished_at=CASE WHEN q.status IN ('CANCELLED','FAILED','COMPLETED') THEN q.finished_at ELSE p.finished_at END,
 updated_at=clock_timestamp()
FROM marketcore_action.command_request_v2 q
WHERE q.process_id=p.process_id AND p.status_code IN ('PENDING','RUNNING')
  AND q.status IN ('CANCELLED','FAILED','COMPLETED');

INSERT INTO marketcore_action.research_process_event_v1
  (process_id,event_code,status_code,progress_pct,step_code,payload)
SELECT q.process_id,'MISCLASSIFICATION_RECONCILED','SKIPPED',100,'COMPLETE',
       jsonb_build_object('old_failure_code',q.failure_code,'cycle_status',c.status_code,
                          'cycle_reason',c.reason_code)
FROM marketcore_action.command_request_v2 q
JOIN marketcore_action.edge_search_request_run_v1 l USING(request_id)
JOIN analytics.edge_search_cycle_status_v1 c USING(cycle_id)
WHERE q.status='FAILED' AND q.failure_code LIKE 'WORKER_VERDICT_MISSING:EDGE_SEARCH_RUN:%'
  AND c.status_code='SKIPPED' AND q.process_id IS NOT NULL;

UPDATE marketcore_action.command_request_v2 q SET
 status='COMPLETED',failure_code=NULL,
 result_reference='VERDICT=AUTONOMOUS_EDGE_SEARCH_RESOURCE_GUARD_OK',
 finished_at=coalesce(q.finished_at,clock_timestamp())
FROM marketcore_action.edge_search_request_run_v1 l
JOIN analytics.edge_search_cycle_status_v1 c USING(cycle_id)
WHERE l.request_id=q.request_id AND q.status='FAILED'
  AND q.failure_code LIKE 'WORKER_VERDICT_MISSING:EDGE_SEARCH_RUN:%'
  AND c.status_code='SKIPPED';

COMMIT;
