CREATE TABLE IF NOT EXISTS presentation.control_center_recommendation_route_v1 (
    reason_group text PRIMARY KEY,
    action_target text NOT NULL,
    enabled boolean NOT NULL DEFAULT true,
    source_version text NOT NULL,
    updated_at timestamptz NOT NULL DEFAULT now()
);

INSERT INTO presentation.control_center_recommendation_route_v1
    (reason_group, action_target, enabled, source_version)
VALUES
    ('DATA', '/workspace-v2/control-center/edge-oos/data-quality?reason_group=DATA', true, 'CONTROL_CENTER_RECOMMENDATION_ROUTES_V1'),
    ('VOLATILITY', '/workspace-v2/control-center/edge-oos/signal-funnel?reason_group=VOLATILITY', true, 'CONTROL_CENTER_RECOMMENDATION_ROUTES_V1'),
    ('LIQUIDITY', '/workspace-v2/control-center/edge-oos/execution-edge?reason_group=LIQUIDITY', true, 'CONTROL_CENTER_RECOMMENDATION_ROUTES_V1'),
    ('RISK', '/workspace-v2/control-center/edge-oos/signal-funnel?reason_group=RISK', true, 'CONTROL_CENTER_RECOMMENDATION_ROUTES_V1'),
    ('EDGE', '/workspace-v2/control-center/edge-oos/relationship-factory?reason_group=EDGE', true, 'CONTROL_CENTER_RECOMMENDATION_ROUTES_V1'),
    ('MARKET', '/workspace-v2/control-center/edge-oos/signal-funnel?reason_group=MARKET', true, 'CONTROL_CENTER_RECOMMENDATION_ROUTES_V1'),
    ('EXIT', '/workspace-v2/control-center/edge-oos/execution-edge?reason_group=EXIT', true, 'CONTROL_CENTER_RECOMMENDATION_ROUTES_V1'),
    ('SETUP', '/workspace-v2/control-center/edge-oos/signal-funnel?reason_group=SETUP', true, 'CONTROL_CENTER_RECOMMENDATION_ROUTES_V1'),
    ('EXECUTION', '/workspace-v2/control-center/edge-oos/execution-edge?reason_group=EXECUTION', true, 'CONTROL_CENTER_RECOMMENDATION_ROUTES_V1'),
    ('RESEARCH', '/workspace-v2/control-center/edge-oos/failure-diagnostics?reason_group=RESEARCH', true, 'CONTROL_CENTER_RECOMMENDATION_ROUTES_V1'),
    ('LIFECYCLE', '/workspace-v2/control-center/edge-oos/failure-diagnostics?reason_group=LIFECYCLE', true, 'CONTROL_CENTER_RECOMMENDATION_ROUTES_V1'),
    ('BLOCK', '/workspace-v2/control-center/edge-oos/signal-funnel?reason_group=BLOCK', true, 'CONTROL_CENTER_RECOMMENDATION_ROUTES_V1'),
    ('QUALITY', '/workspace-v2/control-center/edge-oos/data-quality?reason_group=QUALITY', true, 'CONTROL_CENTER_RECOMMENDATION_ROUTES_V1'),
    ('UNKNOWN', '/workspace-v2/control-center/edge-oos/signal-funnel?reason_group=UNKNOWN', true, 'CONTROL_CENTER_RECOMMENDATION_ROUTES_V1'),
    ('OTHER', '/workspace-v2/control-center/edge-oos/signal-funnel?reason_group=OTHER', true, 'CONTROL_CENTER_RECOMMENDATION_ROUTES_V1')
ON CONFLICT (reason_group) DO UPDATE
SET action_target=EXCLUDED.action_target,
    enabled=EXCLUDED.enabled,
    source_version=EXCLUDED.source_version,
    updated_at=now();

INSERT INTO presentation.ui_resource_v1 (
    resource_key, locale_code, caption, caption_short, caption_mobile,
    tooltip, icon, resource_group
)
VALUES
    ('status.warning', 'ru', 'Требует внимания', 'Внимание', 'Внимание', 'Есть подтверждённая причина для проверки', '', 'status'),
    ('research.recommendation.execute_aria', 'ru', 'Открыть исполнение рекомендации: {reason}', 'Исполнить: {reason}', 'Исполнить', 'Двойной клик открывает экран работы с рекомендацией', '', 'research')
ON CONFLICT (resource_key, locale_code) DO UPDATE
SET caption=EXCLUDED.caption,
    caption_short=EXCLUDED.caption_short,
    caption_mobile=EXCLUDED.caption_mobile,
    tooltip=EXCLUDED.tooltip,
    icon=EXCLUDED.icon,
    resource_group=EXCLUDED.resource_group;
