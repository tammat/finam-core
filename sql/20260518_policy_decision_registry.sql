CREATE TABLE IF NOT EXISTS research_policy_decisions (
    id BIGSERIAL PRIMARY KEY,
    decision_id TEXT NOT NULL,
    report_id TEXT NOT NULL,
    objective TEXT NOT NULL,
    selected_mode TEXT NOT NULL,
    score DOUBLE PRECISION NOT NULL,
    net_pnl DOUBLE PRECISION NOT NULL,
    expectancy DOUBLE PRECISION NOT NULL,
    winrate DOUBLE PRECISION NOT NULL,
    active BOOLEAN NOT NULL DEFAULT false,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    raw_json JSONB NOT NULL DEFAULT '{}'::jsonb
);

CREATE INDEX IF NOT EXISTS idx_research_policy_decisions_active
ON research_policy_decisions(active);

CREATE INDEX IF NOT EXISTS idx_research_policy_decisions_objective
ON research_policy_decisions(objective);

CREATE INDEX IF NOT EXISTS idx_research_policy_decisions_decision_id
ON research_policy_decisions(decision_id);
