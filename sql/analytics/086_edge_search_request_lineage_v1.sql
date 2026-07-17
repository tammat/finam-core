CREATE TABLE IF NOT EXISTS marketcore_action.edge_search_request_run_v1 (
    request_id text PRIMARY KEY REFERENCES marketcore_action.command_request_v2(request_id),
    cycle_id uuid NOT NULL,
    run_id uuid,
    attempt_no integer NOT NULL DEFAULT 1 CHECK(attempt_no BETWEEN 1 AND 2),
    linked_at timestamptz NOT NULL DEFAULT clock_timestamp(),
    updated_at timestamptz NOT NULL DEFAULT clock_timestamp()
);
CREATE UNIQUE INDEX IF NOT EXISTS edge_search_request_run_cycle_idx
ON marketcore_action.edge_search_request_run_v1(cycle_id);
GRANT SELECT,INSERT,UPDATE ON marketcore_action.edge_search_request_run_v1 TO alex;
