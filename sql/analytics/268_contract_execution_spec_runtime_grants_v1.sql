BEGIN;

-- Runtime contract-spec sync executes as role finam.
-- The execution-spec table is owned by alex and therefore did not
-- inherit the expected runtime privileges.

GRANT SELECT, INSERT, UPDATE
ON analytics.market_contract_execution_spec_v2
TO finam;

COMMIT;
