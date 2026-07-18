BEGIN;

ALTER TABLE marketcore_action.command_request_v2 DROP CONSTRAINT IF EXISTS command_request_v2_request_kind_check;
ALTER TABLE marketcore_action.command_request_v2 ADD CONSTRAINT command_request_v2_request_kind_check CHECK (request_kind IN (
 'RESEARCH_REFRESH','PAPER_OBSERVATION','OPERATOR_DECISION_ACKNOWLEDGE','OPERATOR_DECISION_MEASURE',
 'EDGE_SEARCH_RUN','EDGE_SEARCH_CANCEL','RESEARCH_UNIVERSE_INCLUDE','RESEARCH_UNIVERSE_EXCLUDE','RESEARCH_UNIVERSE_PRIORITY'));
ALTER TABLE marketcore_action.command_request_v2 DROP CONSTRAINT IF EXISTS command_request_v2_command_code_check;
ALTER TABLE marketcore_action.command_request_v2 ADD CONSTRAINT command_request_v2_command_code_check CHECK (command_code IN (
 'RESEARCH.REQUEST_REFRESH','PAPER.REQUEST_OBSERVATION','OPERATOR.ACKNOWLEDGE_DECISION','OPERATOR.MEASURE_DECISION',
 'RESEARCH.RUN_EDGE_SEARCH','RESEARCH.CANCEL_EDGE_SEARCH','RESEARCH.UNIVERSE_INCLUDE_NEXT',
 'RESEARCH.UNIVERSE_EXCLUDE_NEXT','RESEARCH.UNIVERSE_SET_PRIORITY'));

ALTER TABLE marketcore_action.research_process_v1 DROP CONSTRAINT IF EXISTS research_process_v1_process_type_check;
ALTER TABLE marketcore_action.research_process_v1 ADD CONSTRAINT research_process_v1_process_type_check CHECK (process_type IN (
 'EDGE_SEARCH','RESEARCH_REFRESH','PAPER_OBSERVATION','OPERATOR_DECISION','RESEARCH_UNIVERSE'));

CREATE OR REPLACE FUNCTION marketcore_action.ensure_research_process_v1() RETURNS trigger LANGUAGE plpgsql AS $$
DECLARE mapped_type text; mapped_recommendation text;
BEGIN
    IF NEW.process_id IS NULL THEN
        mapped_type := CASE
          WHEN NEW.request_kind='EDGE_SEARCH_RUN' THEN 'EDGE_SEARCH'
          WHEN NEW.request_kind='RESEARCH_REFRESH' THEN 'RESEARCH_REFRESH'
          WHEN NEW.request_kind='PAPER_OBSERVATION' THEN 'PAPER_OBSERVATION'
          WHEN NEW.request_kind LIKE 'OPERATOR_DECISION_%' THEN 'OPERATOR_DECISION'
          WHEN NEW.request_kind LIKE 'RESEARCH_UNIVERSE_%' THEN 'RESEARCH_UNIVERSE'
          ELSE NULL END;
        IF mapped_type IS NOT NULL THEN
            NEW.process_id := NEW.request_id::uuid;
            mapped_recommendation := CASE mapped_type
              WHEN 'EDGE_SEARCH' THEN 'KEEP_GATES_AND_EXPAND_EVIDENCE'
              WHEN 'RESEARCH_UNIVERSE' THEN 'APPLY_TO_NEXT_RESEARCH_CYCLE'
              ELSE 'WAIT_FOR_SYSTEM_ANALYSIS' END;
            INSERT INTO marketcore_action.research_process_v1 (
                process_id,process_type,actor_id,recommendation_code,selected_action_id,
                command_request_id,status_code,progress_pct,current_step_code,requested_at,updated_at
            ) VALUES (NEW.process_id,mapped_type,NEW.actor_id,mapped_recommendation,NEW.action_id,
                NEW.request_id,'PENDING',0,'QUEUED',NEW.requested_at,clock_timestamp())
            ON CONFLICT (process_id) DO NOTHING;
            INSERT INTO marketcore_action.research_process_event_v1
                (process_id,event_code,status_code,progress_pct,step_code,payload)
            VALUES (NEW.process_id,'COMMAND_REQUESTED','PENDING',0,'QUEUED',
                jsonb_build_object('request_id',NEW.request_id,'request_kind',NEW.request_kind))
            ON CONFLICT DO NOTHING;
        END IF;
    END IF;
    RETURN NEW;
END $$;

COMMIT;
