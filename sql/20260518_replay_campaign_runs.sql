CREATE TABLE IF NOT EXISTS replay_campaign_runs (
    id BIGSERIAL PRIMARY KEY,

    campaign_id TEXT NOT NULL,
    replay_id TEXT NOT NULL,

    symbol TEXT NOT NULL,
    timeframe TEXT NOT NULL,
    strategy TEXT NOT NULL,

    status TEXT NOT NULL DEFAULT 'unknown',

    started_at TIMESTAMPTZ NOT NULL,
    finished_at TIMESTAMPTZ,

    duration_sec DOUBLE PRECISION NOT NULL DEFAULT 0,

    return_code INTEGER NOT NULL DEFAULT 0,

    command TEXT NOT NULL DEFAULT '',

    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),

    raw_json JSONB NOT NULL DEFAULT '{}'::jsonb
);

CREATE INDEX IF NOT EXISTS idx_replay_campaign_runs_campaign
    ON replay_campaign_runs (campaign_id);

CREATE INDEX IF NOT EXISTS idx_replay_campaign_runs_started
    ON replay_campaign_runs (started_at DESC);

CREATE INDEX IF NOT EXISTS idx_replay_campaign_runs_strategy
    ON replay_campaign_runs (strategy);

CREATE INDEX IF NOT EXISTS idx_replay_campaign_runs_symbol
    ON replay_campaign_runs (symbol);
