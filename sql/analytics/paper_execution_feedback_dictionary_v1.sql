CREATE TABLE IF NOT EXISTS analytics.paper_execution_feedback_reason_group_v1
(
    reason_group_code TEXT PRIMARY KEY,
    reason_group_name TEXT NOT NULL,
    enabled BOOLEAN NOT NULL DEFAULT TRUE,
    source_version TEXT NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS analytics.paper_execution_feedback_severity_v1
(
    severity_code TEXT PRIMARY KEY,
    severity_name TEXT NOT NULL,
    severity_order INTEGER NOT NULL,
    enabled BOOLEAN NOT NULL DEFAULT TRUE,
    source_version TEXT NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS analytics.paper_execution_feedback_reason_v1
(
    reason_code TEXT PRIMARY KEY,

    reason_name TEXT NOT NULL,

    reason_group_code TEXT NOT NULL
        REFERENCES analytics.paper_execution_feedback_reason_group_v1(reason_group_code),

    default_action_code TEXT NOT NULL
        REFERENCES analytics.paper_execution_feedback_action_v1(feedback_action_code),

    default_severity_code TEXT NOT NULL
        REFERENCES analytics.paper_execution_feedback_severity_v1(severity_code),

    enabled BOOLEAN NOT NULL DEFAULT TRUE,

    source_version TEXT NOT NULL,

    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),

    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

INSERT INTO analytics.paper_execution_feedback_reason_group_v1
(reason_group_code,reason_group_name,enabled,source_version)
VALUES
('DATA','Data Quality',TRUE,'PAPER_EXECUTION_FEEDBACK_DICTIONARY_V1'),
('MODEL','Model',TRUE,'PAPER_EXECUTION_FEEDBACK_DICTIONARY_V1'),
('ROBUSTNESS','Robustness',TRUE,'PAPER_EXECUTION_FEEDBACK_DICTIONARY_V1'),
('MARKET','Market',TRUE,'PAPER_EXECUTION_FEEDBACK_DICTIONARY_V1'),
('PROFILE','Trading Profile',TRUE,'PAPER_EXECUTION_FEEDBACK_DICTIONARY_V1'),
('SOURCE','Trading Source',TRUE,'PAPER_EXECUTION_FEEDBACK_DICTIONARY_V1'),
('RISK','Risk',TRUE,'PAPER_EXECUTION_FEEDBACK_DICTIONARY_V1')
ON CONFLICT(reason_group_code)
DO UPDATE SET
reason_group_name=EXCLUDED.reason_group_name,
enabled=EXCLUDED.enabled,
updated_at=now(),
source_version=EXCLUDED.source_version;

INSERT INTO analytics.paper_execution_feedback_severity_v1
(severity_code,severity_name,severity_order,enabled,source_version)
VALUES
('INFO','Information',1,TRUE,'PAPER_EXECUTION_FEEDBACK_DICTIONARY_V1'),
('NOTICE','Notice',2,TRUE,'PAPER_EXECUTION_FEEDBACK_DICTIONARY_V1'),
('WARNING','Warning',3,TRUE,'PAPER_EXECUTION_FEEDBACK_DICTIONARY_V1'),
('CRITICAL','Critical',4,TRUE,'PAPER_EXECUTION_FEEDBACK_DICTIONARY_V1')
ON CONFLICT(severity_code)
DO UPDATE SET
severity_name=EXCLUDED.severity_name,
severity_order=EXCLUDED.severity_order,
enabled=EXCLUDED.enabled,
updated_at=now(),
source_version=EXCLUDED.source_version;

INSERT INTO analytics.paper_execution_feedback_reason_v1
(
reason_code,
reason_name,
reason_group_code,
default_action_code,
default_severity_code,
enabled,
source_version
)
VALUES

('LOW_SAMPLE_SIZE',
'Low Sample Size',
'DATA',
'MORE_DATA_REQUIRED',
'WARNING',
TRUE,
'PAPER_EXECUTION_FEEDBACK_DICTIONARY_V1'),

('NEGATIVE_EXPECTANCY',
'Negative Expectancy',
'MODEL',
'INVESTIGATE',
'WARNING',
TRUE,
'PAPER_EXECUTION_FEEDBACK_DICTIONARY_V1'),

('LOW_PROFIT_FACTOR',
'Low Profit Factor',
'MODEL',
'REVIEW',
'WARNING',
TRUE,
'PAPER_EXECUTION_FEEDBACK_DICTIONARY_V1'),

('HIGH_OVERFIT_RISK',
'High Overfit Risk',
'ROBUSTNESS',
'MORE_DATA_REQUIRED',
'CRITICAL',
TRUE,
'PAPER_EXECUTION_FEEDBACK_DICTIONARY_V1'),

('LOW_ROBUSTNESS',
'Low Robustness',
'ROBUSTNESS',
'INVESTIGATE',
'WARNING',
TRUE,
'PAPER_EXECUTION_FEEDBACK_DICTIONARY_V1'),

('REGIME_UNSTABLE',
'Regime Unstable',
'MARKET',
'REVIEW',
'NOTICE',
TRUE,
'PAPER_EXECUTION_FEEDBACK_DICTIONARY_V1'),

('PROFILE_UNSTABLE',
'Profile Unstable',
'PROFILE',
'REVIEW',
'NOTICE',
TRUE,
'PAPER_EXECUTION_FEEDBACK_DICTIONARY_V1'),

('SOURCE_UNSTABLE',
'Source Unstable',
'SOURCE',
'REVIEW',
'NOTICE',
TRUE,
'PAPER_EXECUTION_FEEDBACK_DICTIONARY_V1')

ON CONFLICT(reason_code)
DO UPDATE SET
reason_name=EXCLUDED.reason_name,
reason_group_code=EXCLUDED.reason_group_code,
default_action_code=EXCLUDED.default_action_code,
default_severity_code=EXCLUDED.default_severity_code,
enabled=EXCLUDED.enabled,
updated_at=now(),
source_version=EXCLUDED.source_version;
