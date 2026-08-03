BEGIN;

CREATE TABLE IF NOT EXISTS analytics.reachable_shadow_challenger_v1 (
    challenger_code text PRIMARY KEY,
    parent_branch_code text NOT NULL REFERENCES analytics.v5_post_fix_branch_registry_v1(branch_code),
    strategy_code text NOT NULL,
    observation_symbol text NOT NULL,
    side_code text NOT NULL CHECK (side_code IN ('LONG','SHORT')),
    candidate_code text NOT NULL,
    frozen_at timestamptz NOT NULL,
    minimum_observations integer NOT NULL DEFAULT 20 CHECK (minimum_observations >= 20),
    minimum_active_days integer NOT NULL DEFAULT 3 CHECK (minimum_active_days >= 3),
    state_code text NOT NULL DEFAULT 'SHADOW_ACCUMULATION'
      CHECK (state_code IN ('SHADOW_ACCUMULATION','READY_FOR_EXPENSIVE_GATES','EARLY_REJECT','RETIRED')),
    paper_allowed boolean NOT NULL DEFAULT false CHECK (paper_allowed = false),
    real_allowed boolean NOT NULL DEFAULT false CHECK (real_allowed = false),
    evidence jsonb NOT NULL DEFAULT '{}'::jsonb,
    created_at timestamptz NOT NULL DEFAULT clock_timestamp(),
    updated_at timestamptz NOT NULL DEFAULT clock_timestamp(),
    UNIQUE(parent_branch_code,candidate_code)
);

ALTER TABLE analytics.reachable_shadow_challenger_v1
  ADD COLUMN IF NOT EXISTS updated_at timestamptz NOT NULL DEFAULT clock_timestamp();

CREATE OR REPLACE VIEW analytics.reachable_shadow_challenger_status_v1 AS
WITH observations AS (
  SELECT c.challenger_code,c.parent_branch_code,c.strategy_code,c.observation_symbol,
         c.side_code,c.candidate_code,c.frozen_at,c.minimum_observations,
         c.minimum_active_days,c.state_code,c.evidence,
         count(p.*)::int matched,
         count(*) FILTER (WHERE p.shadow_entered)::int entered,
         count(*) FILTER (WHERE p.shadow_net_r IS NOT NULL)::int completed,
         count(DISTINCT (p.label_start_ts AT TIME ZONE 'Europe/Moscow')::date)
           FILTER (WHERE p.shadow_net_r IS NOT NULL)::int active_days,
         avg(p.shadow_net_r) FILTER (WHERE p.shadow_net_r IS NOT NULL) expectancy_r,
         avg(p.placebo_net_r) FILTER (WHERE p.shadow_net_r IS NOT NULL
                                      AND p.placebo_net_r IS NOT NULL) placebo_r,
         avg(p.shadow_net_r-p.placebo_net_r) FILTER (WHERE p.shadow_net_r IS NOT NULL
                                                      AND p.placebo_net_r IS NOT NULL) delta_r,
         count(*) FILTER (WHERE p.shadow_exit_reason='GAP_STOP')::int gap_stops,
         max(p.label_end_ts) FILTER (WHERE p.shadow_net_r IS NOT NULL) latest_result_ts
  FROM analytics.reachable_shadow_challenger_v1 c
  LEFT JOIN analytics.entry_exit_signal_shadow_pair_v2 p
    ON p.symbol_code=c.observation_symbol
   AND p.strategy_code=c.strategy_code
   AND p.side_code=c.side_code
   AND p.candidate_code=c.candidate_code
   AND p.label_start_ts>=c.frozen_at
  GROUP BY c.challenger_code,c.parent_branch_code,c.strategy_code,c.observation_symbol,
           c.side_code,c.candidate_code,c.frozen_at,c.minimum_observations,
           c.minimum_active_days,c.state_code,c.evidence
)
SELECT observations.*,
       CASE
         WHEN completed<minimum_observations OR active_days<minimum_active_days
           THEN 'ACCUMULATE'
         WHEN expectancy_r<=0 OR coalesce(delta_r,0)<=0 THEN 'EARLY_REJECT'
         WHEN gap_stops::numeric/nullif(completed,0)>0.25 THEN 'EARLY_REJECT'
         ELSE 'READY_FOR_EXPENSIVE_GATES'
       END AS prospective_verdict
FROM observations;

COMMIT;
