ALTER TABLE marketcore_action.command_request_v2 DROP CONSTRAINT IF EXISTS command_request_v2_request_kind_check;
ALTER TABLE marketcore_action.command_request_v2 ADD CONSTRAINT command_request_v2_request_kind_check CHECK (
 request_kind IN ('RESEARCH_REFRESH','PAPER_OBSERVATION','OPERATOR_DECISION_ACKNOWLEDGE','OPERATOR_DECISION_MEASURE','EDGE_SEARCH_RUN','EDGE_SEARCH_CANCEL'));
ALTER TABLE marketcore_action.command_request_v2 DROP CONSTRAINT IF EXISTS command_request_v2_command_code_check;
ALTER TABLE marketcore_action.command_request_v2 ADD CONSTRAINT command_request_v2_command_code_check CHECK (
 command_code IN ('RESEARCH.REQUEST_REFRESH','PAPER.REQUEST_OBSERVATION','OPERATOR.ACKNOWLEDGE_DECISION','OPERATOR.MEASURE_DECISION','RESEARCH.RUN_EDGE_SEARCH','RESEARCH.CANCEL_EDGE_SEARCH'));
CREATE TABLE IF NOT EXISTS marketcore_action.edge_search_retry_v1(
 source_request_id text PRIMARY KEY REFERENCES marketcore_action.command_request_v2(request_id),
 retry_request_id text NOT NULL UNIQUE REFERENCES marketcore_action.command_request_v2(request_id),
 retry_reason text NOT NULL,created_at timestamptz NOT NULL DEFAULT clock_timestamp());
GRANT SELECT,INSERT ON marketcore_action.edge_search_retry_v1 TO alex;
