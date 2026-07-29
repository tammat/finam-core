BEGIN;

GRANT USAGE ON SCHEMA analytics TO finam;
GRANT SELECT ON analytics.market_contract_cost_spec_v1 TO finam;

COMMIT;
