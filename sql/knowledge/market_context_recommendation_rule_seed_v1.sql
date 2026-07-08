INSERT INTO knowledge.recommendation_rule_v1
(
    rule_code,
    rule_name,
    priority,
    enabled,
    recommendation_code,
    parameter_profile,
    rule_version,
    source_version
)
VALUES
(
    'RULE_VALIDATE_DEFAULT',
    'Default validation rule',
    100,
    TRUE,
    'VALIDATE',
    'PROFILE_DEFAULT',
    1,
    'MARKET_CONTEXT_RECOMMENDATION_RULE_SEED_V1'
),
(
    'RULE_CONTINUE_RESEARCH',
    'Continue research rule',
    200,
    TRUE,
    'CONTINUE_RESEARCH',
    'PROFILE_DEFAULT',
    1,
    'MARKET_CONTEXT_RECOMMENDATION_RULE_SEED_V1'
),
(
    'RULE_OBSERVE',
    'Observation rule',
    300,
    TRUE,
    'OBSERVE',
    'PROFILE_DEFAULT',
    1,
    'MARKET_CONTEXT_RECOMMENDATION_RULE_SEED_V1'
),
(
    'RULE_RECHECK',
    'Recheck rule',
    400,
    TRUE,
    'RECHECK',
    'PROFILE_DEFAULT',
    1,
    'MARKET_CONTEXT_RECOMMENDATION_RULE_SEED_V1'
),
(
    'RULE_REJECT',
    'Reject rule',
    500,
    TRUE,
    'REJECT',
    'PROFILE_DEFAULT',
    1,
    'MARKET_CONTEXT_RECOMMENDATION_RULE_SEED_V1'
)
ON CONFLICT(rule_code)
DO UPDATE SET
    rule_name=EXCLUDED.rule_name,
    priority=EXCLUDED.priority,
    enabled=EXCLUDED.enabled,
    recommendation_code=EXCLUDED.recommendation_code,
    parameter_profile=EXCLUDED.parameter_profile,
    rule_version=EXCLUDED.rule_version,
    updated_at=now(),
    source_version=EXCLUDED.source_version;
