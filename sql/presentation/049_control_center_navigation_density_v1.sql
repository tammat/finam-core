INSERT INTO presentation.ui_theme_property_v1 (
    theme_code, property_code, property_value, property_type,
    description_key, display_order, source_version
)
VALUES
    ('DEFAULT', 'CONTROL_NAV_CARD_MIN_HEIGHT', '54', 'INTEGER', 'ui.theme.property.control_nav_card_min_height', 490, 'CONTROL_CENTER_NAVIGATION_DENSITY_V1'),
    ('DEFAULT', 'CONTROL_NAV_CARD_PADDING', '11', 'INTEGER', 'ui.theme.property.control_nav_card_padding', 500, 'CONTROL_CENTER_NAVIGATION_DENSITY_V1')
ON CONFLICT (theme_code, property_code) DO UPDATE
SET property_value=EXCLUDED.property_value,
    property_type=EXCLUDED.property_type,
    description_key=EXCLUDED.description_key,
    display_order=EXCLUDED.display_order,
    source_version=EXCLUDED.source_version,
    updated_at=now();
