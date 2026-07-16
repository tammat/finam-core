BEGIN;
ALTER TABLE marketcore_action.command_request_v2
    DROP CONSTRAINT IF EXISTS command_request_v2_request_kind_check;
ALTER TABLE marketcore_action.command_request_v2
    ADD CONSTRAINT command_request_v2_request_kind_check CHECK (
        request_kind IN (
            'RESEARCH_REFRESH','EDGE_SEARCH_RUN','PAPER_OBSERVATION',
            'OPERATOR_DECISION_ACKNOWLEDGE','OPERATOR_DECISION_MEASURE'
        )
    );
ALTER TABLE marketcore_action.command_request_v2
    DROP CONSTRAINT IF EXISTS command_request_v2_command_code_check;
ALTER TABLE marketcore_action.command_request_v2
    ADD CONSTRAINT command_request_v2_command_code_check CHECK (
        command_code IN (
            'RESEARCH.REQUEST_REFRESH','RESEARCH.RUN_EDGE_SEARCH','PAPER.REQUEST_OBSERVATION',
            'OPERATOR.ACKNOWLEDGE_DECISION','OPERATOR.MEASURE_DECISION'
        )
    );
COMMIT;
