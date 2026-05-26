CREATE TABLE IF NOT EXISTS replay_campaign_runs (
    id BIGSERIAL PRIMARY KEY
);

ALTER TABLE replay_campaign_runs
ADD COLUMN IF NOT EXISTS campaign_id TEXT NOT NULL DEFAULT 'unknown';

ALTER TABLE replay_campaign_runs
ADD COLUMN IF NOT EXISTS symbol TEXT NOT NULL DEFAULT '';

ALTER TABLE replay_campaign_runs
ADD COLUMN IF NOT EXISTS strategy TEXT NOT NULL DEFAULT 'BR_CONSERVATIVE_BREAKOUT';

ALTER TABLE replay_campaign_runs
ADD COLUMN IF NOT EXISTS timeframe TEXT NOT NULL DEFAULT 'M5';

ALTER TABLE replay_campaign_runs
ADD COLUMN IF NOT EXISTS from_ts TIMESTAMPTZ;

ALTER TABLE replay_campaign_runs
ADD COLUMN IF NOT EXISTS to_ts TIMESTAMPTZ;

ALTER TABLE replay_campaign_runs
ADD COLUMN IF NOT EXISTS window_index INTEGER NOT NULL DEFAULT 0;

ALTER TABLE replay_campaign_runs
ADD COLUMN IF NOT EXISTS signals INTEGER NOT NULL DEFAULT 0;

ALTER TABLE replay_campaign_runs
ADD COLUMN IF NOT EXISTS paper_orders INTEGER NOT NULL DEFAULT 0;

ALTER TABLE replay_campaign_runs
ADD COLUMN IF NOT EXISTS trades_logged INTEGER NOT NULL DEFAULT 0;

ALTER TABLE replay_campaign_runs
ADD COLUMN IF NOT EXISTS min_trade_id BIGINT;

ALTER TABLE replay_campaign_runs
ADD COLUMN IF NOT EXISTS max_trade_id BIGINT;

ALTER TABLE replay_campaign_runs
ADD COLUMN IF NOT EXISTS closed_trades INTEGER NOT NULL DEFAULT 0;

ALTER TABLE replay_campaign_runs
ADD COLUMN IF NOT EXISTS net_pnl DOUBLE PRECISION NOT NULL DEFAULT 0;

ALTER TABLE replay_campaign_runs
ADD COLUMN IF NOT EXISTS winrate DOUBLE PRECISION NOT NULL DEFAULT 0;

ALTER TABLE replay_campaign_runs
ADD COLUMN IF NOT EXISTS created_at TIMESTAMPTZ NOT NULL DEFAULT now();

CREATE UNIQUE INDEX IF NOT EXISTS ux_replay_campaign_runs_campaign_symbol_window
ON replay_campaign_runs(campaign_id, symbol, window_index);

CREATE INDEX IF NOT EXISTS idx_replay_campaign_runs_symbol_created
ON replay_campaign_runs(symbol, created_at DESC);

CREATE INDEX IF NOT EXISTS idx_replay_campaign_runs_campaign
ON replay_campaign_runs(campaign_id, window_index);
