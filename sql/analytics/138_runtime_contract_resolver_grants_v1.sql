BEGIN;

GRANT USAGE ON SCHEMA analytics TO finam;
GRANT SELECT ON analytics.futures_roll_decision_v1 TO finam;
GRANT SELECT ON public.futures_contract_calendar TO finam;

COMMIT;
