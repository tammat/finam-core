INSERT INTO presentation.ui_theme_property_v1 (
    theme_code, property_code, property_value, property_type,
    description_key, display_order, source_version
)
VALUES
    ('DEFAULT', 'CONTROL_KPI_MIN_WIDTH', '145', 'INTEGER', 'ui.theme.property.control_kpi_min_width', 410, 'CONTROL_CENTER_COMPACT_THEME_V1'),
    ('DEFAULT', 'CONTROL_GRID_GAP', '10', 'INTEGER', 'ui.theme.property.control_grid_gap', 420, 'CONTROL_CENTER_COMPACT_THEME_V1'),
    ('DEFAULT', 'CONTROL_CARD_MIN_HEIGHT', '108', 'INTEGER', 'ui.theme.property.control_card_min_height', 430, 'CONTROL_CENTER_COMPACT_THEME_V1'),
    ('DEFAULT', 'CONTROL_CARD_PADDING', '13', 'INTEGER', 'ui.theme.property.control_card_padding', 440, 'CONTROL_CENTER_COMPACT_THEME_V1'),
    ('DEFAULT', 'CONTROL_CARD_RADIUS', '12', 'INTEGER', 'ui.theme.property.control_card_radius', 450, 'CONTROL_CENTER_COMPACT_THEME_V1'),
    ('DEFAULT', 'CONTROL_KPI_FONT_SIZE', '18', 'INTEGER', 'ui.theme.property.control_kpi_font_size', 460, 'CONTROL_CENTER_COMPACT_THEME_V1'),
    ('DEFAULT', 'CONTROL_KPI_FONT_WEIGHT', '600', 'INTEGER', 'ui.theme.property.control_kpi_font_weight', 470, 'CONTROL_CENTER_COMPACT_THEME_V1')
ON CONFLICT (theme_code, property_code) DO UPDATE
SET property_value = EXCLUDED.property_value,
    property_type = EXCLUDED.property_type,
    description_key = EXCLUDED.description_key,
    display_order = EXCLUDED.display_order,
    source_version = EXCLUDED.source_version,
    updated_at = now();

INSERT INTO presentation.ui_resource_v1 (
    resource_key, locale_code, caption, caption_short, caption_mobile,
    tooltip, icon, resource_group
)
VALUES
    ('column.loss_reason', 'ru', 'Причина', 'Причина', 'Причина', 'Подтверждённая причина потери сигнала', '', 'column'),
    ('column.event_count', 'ru', 'Количество', 'Кол-во', 'Кол-во', 'Количество зарегистрированных событий', '', 'column'),
    ('column.recommended_action', 'ru', 'Рекомендуемое действие', 'Действие', 'Действие', 'Следующее действие оператора', '', 'column')
ON CONFLICT (resource_key, locale_code) DO UPDATE
SET caption = EXCLUDED.caption,
    caption_short = EXCLUDED.caption_short,
    caption_mobile = EXCLUDED.caption_mobile,
    tooltip = EXCLUDED.tooltip,
    icon = EXCLUDED.icon,
    resource_group = EXCLUDED.resource_group;
