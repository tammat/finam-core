BEGIN;
CREATE TABLE IF NOT EXISTS marketcore_action.command_request_v2 (
    request_id TEXT PRIMARY KEY,
    action_id TEXT NOT NULL,
    request_kind TEXT NOT NULL CHECK (request_kind IN ('RESEARCH_REFRESH','PAPER_OBSERVATION')),
    command_code TEXT NOT NULL CHECK (command_code IN ('RESEARCH.REQUEST_REFRESH','PAPER.REQUEST_OBSERVATION')),
    actor_id TEXT NOT NULL,
    status TEXT NOT NULL CHECK (status IN ('PENDING','RUNNING','COMPLETED','FAILED','CANCELLED')),
    requested_at TIMESTAMPTZ NOT NULL,
    started_at TIMESTAMPTZ,
    finished_at TIMESTAMPTZ,
    result_reference TEXT,
    failure_code TEXT
);
CREATE INDEX IF NOT EXISTS command_request_v2_status_time_idx ON marketcore_action.command_request_v2(status,requested_at);
COMMIT;
