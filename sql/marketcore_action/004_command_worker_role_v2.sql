BEGIN;

DO $$
BEGIN
    IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'finam') THEN
        GRANT USAGE ON SCHEMA marketcore_action TO finam;
        GRANT SELECT, UPDATE ON marketcore_action.command_request_v2 TO finam;
        GRANT INSERT ON marketcore_action.action_audit_v2 TO finam;
        GRANT USAGE, SELECT ON SEQUENCE marketcore_action.action_audit_v2_audit_id_seq TO finam;
    END IF;
END
$$;

COMMIT;
