INSERT INTO presentation.ui_theme_property_v1 (
    theme_code, property_code, property_value, property_type,
    description_key, display_order, source_version
)
VALUES
    ('DEFAULT', 'CONTROL_CARD_MIN_HEIGHT', '82', 'INTEGER', 'ui.theme.property.control_card_min_height', 430, 'CONTROL_CENTER_COMPACT_VALUES_V1'),
    ('DEFAULT', 'CONTROL_CARD_PADDING', '10', 'INTEGER', 'ui.theme.property.control_card_padding', 440, 'CONTROL_CENTER_COMPACT_VALUES_V1'),
    ('DEFAULT', 'CONTROL_CARD_RADIUS', '10', 'INTEGER', 'ui.theme.property.control_card_radius', 450, 'CONTROL_CENTER_COMPACT_VALUES_V1'),
    ('DEFAULT', 'CONTROL_KPI_FONT_SIZE', '12', 'INTEGER', 'ui.theme.property.control_kpi_font_size', 460, 'CONTROL_CENTER_COMPACT_VALUES_V1'),
    ('DEFAULT', 'CONTROL_KPI_FONT_WEIGHT', '600', 'INTEGER', 'ui.theme.property.control_kpi_font_weight', 470, 'CONTROL_CENTER_COMPACT_VALUES_V1'),
    ('DEFAULT', 'CONTROL_NAV_CARD_MIN_HEIGHT', '44', 'INTEGER', 'ui.theme.property.control_nav_card_min_height', 490, 'CONTROL_CENTER_COMPACT_VALUES_V1'),
    ('DEFAULT', 'CONTROL_NAV_CARD_PADDING', '9', 'INTEGER', 'ui.theme.property.control_nav_card_padding', 500, 'CONTROL_CENTER_COMPACT_VALUES_V1')
ON CONFLICT (theme_code, property_code) DO UPDATE
SET property_value=EXCLUDED.property_value,
    property_type=EXCLUDED.property_type,
    description_key=EXCLUDED.description_key,
    display_order=EXCLUDED.display_order,
    source_version=EXCLUDED.source_version,
    updated_at=now();
