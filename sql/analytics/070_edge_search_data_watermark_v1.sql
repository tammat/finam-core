BEGIN;
ALTER TABLE analytics.edge_search_cycle_status_v1
    ADD COLUMN IF NOT EXISTS market_data_watermark TIMESTAMPTZ;
ALTER TABLE analytics.edge_search_cycle_status_v1
    DROP CONSTRAINT IF EXISTS edge_search_cycle_status_v1_status_code_check;
ALTER TABLE analytics.edge_search_cycle_status_v1
    ADD CONSTRAINT edge_search_cycle_status_v1_status_code_check CHECK (status_code IN (
        'RUNNING','PASS_FOUND','NO_PASS','NO_CURRENT_MARKETS','FAILED','SKIPPED'
    ));
COMMIT;
