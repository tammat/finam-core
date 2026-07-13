CREATE TABLE IF NOT EXISTS presentation.control_center_reason_policy_v1 (
    reason_group text NOT NULL,
    source_schema text NOT NULL,
    source_table text NOT NULL,
    reason_column text NOT NULL,
    reason_value_pattern text NOT NULL,
    enabled boolean NOT NULL DEFAULT true,
    source_version text NOT NULL,
    updated_at timestamptz NOT NULL DEFAULT now(),
    PRIMARY KEY (reason_group, source_schema, source_table, reason_column, reason_value_pattern)
);

INSERT INTO presentation.control_center_reason_policy_v1
    (reason_group,source_schema,source_table,reason_column,reason_value_pattern,enabled,source_version)
VALUES
    ('RISK','public','runtime_allocator_decisions','decision_reason','^rejected_by_limit$',true,'CONTROL_CENTER_REASON_POLICY_V1'),
    ('RISK','analytics','risk_decision_snapshot_v1','risk_decision_code','^RISK_BLOCK$',true,'CONTROL_CENTER_REASON_POLICY_V1'),
    ('RISK','public','risk_event_audit_v1','reason','^daily_loss_limit$',true,'CONTROL_CENTER_REASON_POLICY_V1'),
    ('RISK','analytics','paper_execution_feedback_v1','feedback_reason_code','^HIGH_OVERFIT_RISK$',true,'CONTROL_CENTER_REASON_POLICY_V1'),
    ('RISK','public','runtime_governance_decisions','reason','event_risk=EVENT_ACTIVE',true,'CONTROL_CENTER_REASON_POLICY_V1'),
    ('VOLATILITY','public','runtime_guard_pre_signal_block_audit_v1','block_reason','^br_volatility_too_low$',true,'CONTROL_CENTER_REASON_POLICY_V1'),
    ('SETUP','public','runtime_guard_pre_signal_block_audit_v1','block_reason','^compression_watch_active$',true,'CONTROL_CENTER_REASON_POLICY_V1'),
    ('SETUP','public','trade_context_snapshots','reason','^(smart_entry_retest|smart_entry_retest_br_manual_candidate|historical_breakout_buy)$',true,'CONTROL_CENTER_REASON_POLICY_V1'),
    ('EXECUTION','public','order_reconciliation_issues','reason','^ack_order_id_not_found_in_broker_orders$',true,'CONTROL_CENTER_REASON_POLICY_V1'),
    ('EXECUTION','public','execution_events','reason','^real_order_confirm_disabled$',true,'CONTROL_CENTER_REASON_POLICY_V1'),
    ('EXECUTION','public','execution_intents','reason','^(broker_status=ORDER_STATUS_CANCELED|BROKER_UNCOVERED_POSITION_WARNING)$',true,'CONTROL_CENTER_REASON_POLICY_V1'),
    ('EXIT','public','trade_context_snapshots','reason','^(time_exit|historical_time_exit|stop_loss_long|stall_exit_long)$',true,'CONTROL_CENTER_REASON_POLICY_V1'),
    ('EXIT','public','signal_lifecycle','close_reason','^TIME_EXPIRED$',true,'CONTROL_CENTER_REASON_POLICY_V1'),
    ('BLOCK','public','runtime_candidate_decision_board','decision_reason','^candidate_rejected_or_not_ready$',true,'CONTROL_CENTER_REASON_POLICY_V1'),
    ('BLOCK','public','runtime_governance_decisions','decision','^BLOCK_RUNTIME_SELECTION$',true,'CONTROL_CENTER_REASON_POLICY_V1'),
    ('BLOCK','public','risk_event_audit_v1','decision','^REJECT$',true,'CONTROL_CENTER_REASON_POLICY_V1'),
    ('DATA','analytics','paper_execution_feedback_v1','feedback_reason_code','^LOW_SAMPLE_SIZE$',true,'CONTROL_CENTER_REASON_POLICY_V1'),
    ('EDGE','public','runtime_candidate_lifecycle_board','event_reason','^negative_expectancy$',true,'CONTROL_CENTER_REASON_POLICY_V1'),
    ('EDGE','knowledge','recommendation_reason_v1','reason_code','^reason.edge_score.ge$',true,'CONTROL_CENTER_REASON_POLICY_V1'),
    ('EDGE','analytics','paper_execution_feedback_v1','feedback_reason_code','^NEGATIVE_EXPECTANCY$',true,'CONTROL_CENTER_REASON_POLICY_V1'),
    ('QUALITY','public','runtime_candidate_lifecycle_board','event_reason','^loss_tail_filter_unstable$',true,'CONTROL_CENTER_REASON_POLICY_V1'),
    ('QUALITY','analytics','recommendation_feedback_v1','decision_outcome','^NO_EFFECT$',true,'CONTROL_CENTER_REASON_POLICY_V1'),
    ('UNKNOWN','public','trade_context_snapshots','heat_status','^unknown$',true,'CONTROL_CENTER_REASON_POLICY_V1'),
    ('MARKET','public','execution_intents','reason','^manual_reconcile_after_real_market_buy_fill$',true,'CONTROL_CENTER_REASON_POLICY_V1')
ON CONFLICT (reason_group,source_schema,source_table,reason_column,reason_value_pattern) DO UPDATE
SET enabled=EXCLUDED.enabled,
    source_version=EXCLUDED.source_version,
    updated_at=now();

ALTER TABLE presentation.control_center_recommendation_route_v1
    ALTER COLUMN action_target DROP NOT NULL;

UPDATE presentation.control_center_recommendation_route_v1
SET action_target = CASE reason_group
    WHEN 'DATA' THEN '/workspace-v2/control-center/edge-oos#state'
    WHEN 'QUALITY' THEN '/workspace-v2/control-center/edge-oos#state'
    WHEN 'EDGE' THEN '/workspace-v2/control-center/edge-oos#relationship-factory'
    WHEN 'RESEARCH' THEN '/workspace-v2/control-center/edge-oos#relationship-factory'
    ELSE NULL
END,
source_version='CONTROL_CENTER_REASON_POLICY_V1',
updated_at=now();

INSERT INTO presentation.ui_resource_v1 (
    resource_key,locale_code,caption,caption_short,caption_mobile,
    tooltip,icon,resource_group
)
VALUES (
    'status.execution_section_missing','ru','Раздел исполнения не реализован',
    'Нет раздела','Нет раздела','Для этой рекомендации пока нет отдельного рабочего раздела','','status'
)
ON CONFLICT (resource_key,locale_code) DO UPDATE
SET caption=EXCLUDED.caption,caption_short=EXCLUDED.caption_short,
    caption_mobile=EXCLUDED.caption_mobile,tooltip=EXCLUDED.tooltip,
    icon=EXCLUDED.icon,resource_group=EXCLUDED.resource_group;
