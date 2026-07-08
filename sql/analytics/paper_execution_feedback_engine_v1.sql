ALTER TABLE analytics.paper_execution_feedback_v1
ADD COLUMN IF NOT EXISTS feedback_reason_code TEXT;

ALTER TABLE analytics.paper_execution_feedback_v1
ADD COLUMN IF NOT EXISTS feedback_severity_code TEXT;

CREATE TABLE IF NOT EXISTS analytics.paper_execution_feedback_rule_v1 (
    feedback_rule_code TEXT PRIMARY KEY,
    metric_source TEXT NOT NULL,
    metric_code TEXT NOT NULL,
    operator_code TEXT NOT NULL,
    threshold_parameter_code TEXT NOT NULL,
    feedback_scope_code TEXT NOT NULL
        REFERENCES analytics.paper_execution_feedback_scope_v1(feedback_scope_code),
    reason_code TEXT NOT NULL
        REFERENCES analytics.paper_execution_feedback_reason_v1(reason_code),
    enabled BOOLEAN NOT NULL DEFAULT TRUE,
    source_version TEXT NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

INSERT INTO knowledge.platform_parameter_v1
(parameter_code, parameter_name, parameter_group, parameter_type, parameter_value, description, enabled, source_version)
VALUES
('PAPER_FEEDBACK_ZERO_THRESHOLD', 'Zero threshold', 'PAPER_FEEDBACK', 'NUMERIC', '0', 'Zero threshold for negative metrics', TRUE, 'PAPER_EXECUTION_FEEDBACK_ENGINE_V1'),
('PAPER_FEEDBACK_HIGH_OVERFIT_VALUE', 'High overfit value', 'PAPER_FEEDBACK', 'TEXT', 'HIGH', 'High overfit risk value', TRUE, 'PAPER_EXECUTION_FEEDBACK_ENGINE_V1')
ON CONFLICT(parameter_code)
DO UPDATE SET
  parameter_name=EXCLUDED.parameter_name,
  parameter_group=EXCLUDED.parameter_group,
  parameter_type=EXCLUDED.parameter_type,
  parameter_value=EXCLUDED.parameter_value,
  description=EXCLUDED.description,
  enabled=EXCLUDED.enabled,
  source_version=EXCLUDED.source_version,
  updated_at=now();

INSERT INTO analytics.paper_execution_feedback_rule_v1
(feedback_rule_code, metric_source, metric_code, operator_code, threshold_parameter_code, feedback_scope_code, reason_code, enabled, source_version)
VALUES
('RULE_ROBUSTNESS_LOW_SAMPLE', 'ROBUSTNESS', 'sample_trades', 'LT', 'ROBUSTNESS_VALIDATED_MIN_TRADES', 'KNOWLEDGE', 'LOW_SAMPLE_SIZE', TRUE, 'PAPER_EXECUTION_FEEDBACK_ENGINE_V1'),
('RULE_ROBUSTNESS_HIGH_OVERFIT', 'ROBUSTNESS', 'overfit_risk', 'EQ', 'PAPER_FEEDBACK_HIGH_OVERFIT_VALUE', 'KNOWLEDGE', 'HIGH_OVERFIT_RISK', TRUE, 'PAPER_EXECUTION_FEEDBACK_ENGINE_V1'),
('RULE_PROFILE_NEGATIVE_EXPECTANCY', 'PROFILE', 'expectancy_r', 'LT', 'PAPER_FEEDBACK_ZERO_THRESHOLD', 'PROFILE', 'NEGATIVE_EXPECTANCY', TRUE, 'PAPER_EXECUTION_FEEDBACK_ENGINE_V1'),
('RULE_SOURCE_NEGATIVE_EXPECTANCY', 'SOURCE', 'expectancy_r', 'LT', 'PAPER_FEEDBACK_ZERO_THRESHOLD', 'SOURCE', 'NEGATIVE_EXPECTANCY', TRUE, 'PAPER_EXECUTION_FEEDBACK_ENGINE_V1'),
('RULE_REGIME_NEGATIVE_EXPECTANCY', 'REGIME', 'expectancy_r', 'LT', 'PAPER_FEEDBACK_ZERO_THRESHOLD', 'REGIME', 'NEGATIVE_EXPECTANCY', TRUE, 'PAPER_EXECUTION_FEEDBACK_ENGINE_V1')
ON CONFLICT(feedback_rule_code)
DO UPDATE SET
  metric_source=EXCLUDED.metric_source,
  metric_code=EXCLUDED.metric_code,
  operator_code=EXCLUDED.operator_code,
  threshold_parameter_code=EXCLUDED.threshold_parameter_code,
  feedback_scope_code=EXCLUDED.feedback_scope_code,
  reason_code=EXCLUDED.reason_code,
  enabled=EXCLUDED.enabled,
  source_version=EXCLUDED.source_version,
  updated_at=now();
