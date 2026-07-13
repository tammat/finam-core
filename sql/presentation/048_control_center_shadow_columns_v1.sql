INSERT INTO presentation.ui_theme_property_v1 (
    theme_code, property_code, property_value, property_type,
    description_key, display_order, source_version
)
VALUES (
    'DEFAULT', 'CONTROL_SHADOW_COLUMNS', '10', 'INTEGER',
    'ui.theme.property.control_shadow_columns', 480,
    'CONTROL_CENTER_SHADOW_COLUMNS_V1'
)
ON CONFLICT (theme_code, property_code) DO UPDATE
SET property_value=EXCLUDED.property_value,
    property_type=EXCLUDED.property_type,
    description_key=EXCLUDED.description_key,
    display_order=EXCLUDED.display_order,
    source_version=EXCLUDED.source_version,
    updated_at=now();
