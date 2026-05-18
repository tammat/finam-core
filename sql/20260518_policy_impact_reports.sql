CREATE TABLE IF NOT EXISTS research_policy_impact_reports (
    id BIGSERIAL PRIMARY KEY,
    report_id TEXT NOT NULL,
    base_campaign_id TEXT NOT NULL,
    limited_campaign_id TEXT NOT NULL,
    selective_campaign_id TEXT NOT NULL,

    base_trades INTEGER NOT NULL,
    limited_trades INTEGER NOT NULL,
    selective_trades INTEGER NOT NULL,

    base_net_pnl DOUBLE PRECISION NOT NULL,
    limited_net_pnl DOUBLE PRECISION NOT NULL,
    selective_net_pnl DOUBLE PRECISION NOT NULL,

    base_expectancy DOUBLE PRECISION NOT NULL,
    limited_expectancy DOUBLE PRECISION NOT NULL,
    selective_expectancy DOUBLE PRECISION NOT NULL,

    base_winrate DOUBLE PRECISION NOT NULL,
    limited_winrate DOUBLE PRECISION NOT NULL,
    selective_winrate DOUBLE PRECISION NOT NULL,

    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    raw_json JSONB NOT NULL DEFAULT '{}'::jsonb
);

CREATE INDEX IF NOT EXISTS idx_policy_impact_reports_report_id
ON research_policy_impact_reports(report_id);

CREATE INDEX IF NOT EXISTS idx_policy_impact_reports_created_at
ON research_policy_impact_reports(created_at);
