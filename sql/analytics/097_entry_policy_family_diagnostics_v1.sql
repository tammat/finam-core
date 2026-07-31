BEGIN;

CREATE TABLE IF NOT EXISTS analytics.entry_exit_shadow_diagnostic_v1 (
  source_signal_id BIGINT NOT NULL,
  candidate_code TEXT NOT NULL,
  entry_delay_bars INTEGER,
  entry_slippage_r NUMERIC,
  mfe_r NUMERIC,
  mae_r NUMERIC,
  exit_efficiency NUMERIC,
  generated_at TIMESTAMPTZ NOT NULL DEFAULT clock_timestamp(),
  PRIMARY KEY(source_signal_id,candidate_code)
);
GRANT SELECT,INSERT,UPDATE ON analytics.entry_exit_shadow_diagnostic_v1 TO alex,finam;

ALTER TABLE analytics.adaptive_regime_paper_pilot_v1
  DROP CONSTRAINT IF EXISTS adaptive_regime_paper_pilot_v1_status_code_check;
ALTER TABLE analytics.adaptive_regime_paper_pilot_v1
  ADD CONSTRAINT adaptive_regime_paper_pilot_v1_status_code_check CHECK (
    status_code IN (
      'SHADOW_COLLECTING','PILOT_ACTIVE','PAPER_CONFIRMED',
      'ROLLED_BACK','SUPERSEDED'
    )
  );

CREATE OR REPLACE VIEW analytics.entry_policy_family_diagnostics_v1 AS
SELECT symbol,side_code,strategy_code,regime_code,
       CASE entry_mode
         WHEN 'ADAPTIVE' THEN 'ADAPTIVE_OR_SKIP'
         WHEN 'CONFIRM_1' THEN 'CONFIRM_1'
         WHEN 'RETEST_3' THEN 'RETEST_3'
         ELSE entry_mode
       END policy_family,
       count(*) candidates,
       sum(shadow_observations) shadow_observations,
       round(avg(shadow_expectancy),4) expectancy_r,
       round(avg(shadow_profit_factor),3) profit_factor,
       max(status_code) FILTER (
         WHERE status_code IN ('PILOT_ACTIVE','PAPER_CONFIRMED')
       ) active_status,
       max(evaluated_at) evaluated_at
FROM analytics.adaptive_regime_paper_pilot_v1
WHERE status_code<>'SUPERSEDED'
GROUP BY symbol,side_code,strategy_code,regime_code,policy_family;

GRANT SELECT ON analytics.entry_policy_family_diagnostics_v1 TO alex,finam;
COMMIT;
