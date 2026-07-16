BEGIN;
CREATE TABLE IF NOT EXISTS analytics.profit_funnel_shadow_paper_admission_v2 (
    admission_id UUID PRIMARY KEY,
    incubator_candidate_id UUID NOT NULL,
    cohort_id UUID NOT NULL,
    closed_trades BIGINT NOT NULL CHECK (closed_trades >= 0),
    active_trades BIGINT NOT NULL CHECK (active_trades >= 0),
    net_pnl NUMERIC NOT NULL,
    observed_calendar_days INTEGER NOT NULL CHECK (observed_calendar_days >= 0),
    minimum_observations INTEGER NOT NULL,
    minimum_calendar_days INTEGER NOT NULL,
    admission_status TEXT NOT NULL CHECK (admission_status IN ('ELIGIBLE','WAITING','REJECTED')),
    reason_code TEXT NOT NULL,
    paper_candidate_id UUID NOT NULL UNIQUE,
    paper_allowed BOOLEAN NOT NULL DEFAULT FALSE,
    runtime_allowed BOOLEAN NOT NULL DEFAULT FALSE,
    live_allowed BOOLEAN NOT NULL DEFAULT FALSE,
    source_version TEXT NOT NULL,
    evaluated_at TIMESTAMPTZ NOT NULL DEFAULT clock_timestamp(),
    UNIQUE (cohort_id,incubator_candidate_id),
    CHECK (NOT paper_allowed AND NOT runtime_allowed AND NOT live_allowed)
);
REVOKE INSERT, UPDATE, DELETE, TRUNCATE ON analytics.profit_funnel_shadow_paper_admission_v2 FROM PUBLIC;
GRANT SELECT, INSERT, UPDATE ON analytics.profit_funnel_shadow_paper_admission_v2 TO alex;
COMMIT;
