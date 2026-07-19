BEGIN;

GRANT USAGE ON SCHEMA analytics TO finam;
GRANT SELECT ON analytics.signal_intake_policy_v2 TO finam;
GRANT SELECT,INSERT,UPDATE ON analytics.signal_intake_queue_v2 TO finam;

COMMIT;
