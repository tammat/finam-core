BEGIN;

-- CONTRACT_SPEC_SYNC_V1 executes under runtime role finam.
-- These objects are owned by alex, therefore the platform-wide
-- ALTER DEFAULT PRIVILEGES established by another owner did not
-- propagate to them.

GRANT SELECT, INSERT, UPDATE
ON analytics.contract_spec_sync_run_v1
TO finam;

GRANT SELECT, INSERT
ON analytics.contract_spec_sync_item_v1
TO finam;

GRANT USAGE, SELECT
ON SEQUENCE analytics.contract_spec_sync_item_v1_item_id_seq
TO finam;

GRANT SELECT, INSERT, UPDATE
ON analytics.market_contract_cost_spec_v1
TO finam;

COMMIT;
