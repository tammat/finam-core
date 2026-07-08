INSERT INTO analytics.paper_execution_feedback_scope_v1
(feedback_scope_code, feedback_scope_name, enabled, source_version)
VALUES
('PROFILE', 'Trading profile feedback', TRUE, 'PAPER_EXECUTION_FEEDBACK_SCHEMA_V1'),
('SOURCE', 'Trading source feedback', TRUE, 'PAPER_EXECUTION_FEEDBACK_SCHEMA_V1'),
('REGIME', 'Market regime feedback', TRUE, 'PAPER_EXECUTION_FEEDBACK_SCHEMA_V1'),
('KNOWLEDGE', 'Knowledge layer feedback', TRUE, 'PAPER_EXECUTION_FEEDBACK_SCHEMA_V1'),
('RECOMMENDATION', 'Recommendation feedback', TRUE, 'PAPER_EXECUTION_FEEDBACK_SCHEMA_V1'),
('TRADING_PLAN', 'Trading plan feedback', TRUE, 'PAPER_EXECUTION_FEEDBACK_SCHEMA_V1'),
('RISK', 'Risk feedback', TRUE, 'PAPER_EXECUTION_FEEDBACK_SCHEMA_V1'),
('PORTFOLIO', 'Portfolio feedback', TRUE, 'PAPER_EXECUTION_FEEDBACK_SCHEMA_V1')
ON CONFLICT(feedback_scope_code)
DO UPDATE SET
  feedback_scope_name=EXCLUDED.feedback_scope_name,
  enabled=EXCLUDED.enabled,
  source_version=EXCLUDED.source_version,
  updated_at=now();

INSERT INTO analytics.paper_execution_feedback_action_v1
(feedback_action_code, feedback_action_name, enabled, source_version)
VALUES
('KEEP', 'Keep current configuration', TRUE, 'PAPER_EXECUTION_FEEDBACK_SCHEMA_V1'),
('REVIEW', 'Review manually', TRUE, 'PAPER_EXECUTION_FEEDBACK_SCHEMA_V1'),
('INVESTIGATE', 'Investigate further', TRUE, 'PAPER_EXECUTION_FEEDBACK_SCHEMA_V1'),
('PROMOTE_CANDIDATE', 'Promote candidate after approval', TRUE, 'PAPER_EXECUTION_FEEDBACK_SCHEMA_V1'),
('MORE_DATA_REQUIRED', 'More data required', TRUE, 'PAPER_EXECUTION_FEEDBACK_SCHEMA_V1'),
('DISABLE_CANDIDATE', 'Disable candidate after approval', TRUE, 'PAPER_EXECUTION_FEEDBACK_SCHEMA_V1')
ON CONFLICT(feedback_action_code)
DO UPDATE SET
  feedback_action_name=EXCLUDED.feedback_action_name,
  enabled=EXCLUDED.enabled,
  source_version=EXCLUDED.source_version,
  updated_at=now();
