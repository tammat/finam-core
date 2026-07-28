BEGIN;
ALTER TABLE analytics.archive_v3_oos_bridge_v1
    ADD COLUMN IF NOT EXISTS v3_net_pnl numeric NOT NULL DEFAULT 0;
COMMIT;
