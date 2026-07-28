ALTER TABLE analytics.trade_outcome_hypothesis_v1
    ADD COLUMN IF NOT EXISTS regime_code TEXT;

ALTER TABLE analytics.trade_outcome_hypothesis_v1
    DROP CONSTRAINT IF EXISTS trade_outcome_hypothesis_v1_hypothesis_type_check;

ALTER TABLE analytics.trade_outcome_hypothesis_v1
    ADD CONSTRAINT trade_outcome_hypothesis_v1_hypothesis_type_check
    CHECK (hypothesis_type IN (
        'FILTER_OOS_CANDIDATE','DATA_QUALITY_REMEDIATION',
        'LOSS_FILTER_REMEDIATION','SAMPLE_EXPANSION',
        'SESSION_FILTER_COHORT','EXIT_POLICY_REFINEMENT','REGIME_FILTER_COHORT'
    ));

COMMENT ON COLUMN analytics.trade_outcome_hypothesis_v1.regime_code IS
    'Рыночный режим для отдельной исследовательской гипотезы; не является допуском.';
