UPDATE analytics.risk_configuration_v1
SET config_json = config_json || jsonb_build_object(
        'presentation_freshness_seconds',
        COALESCE(config_json->'presentation_freshness_seconds', to_jsonb(900))
    ),
    updated_at = now()
WHERE risk_name = 'DEFAULT'
  AND NOT (config_json ? 'presentation_freshness_seconds');
