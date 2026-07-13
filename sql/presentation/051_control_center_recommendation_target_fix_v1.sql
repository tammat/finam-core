UPDATE presentation.control_center_recommendation_route_v1
SET action_target = '/workspace-v2/control-center/edge-oos?reason_group=' || reason_group,
    source_version = 'CONTROL_CENTER_RECOMMENDATION_TARGET_FIX_V1',
    updated_at = now()
WHERE enabled;
