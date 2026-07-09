INSERT INTO presentation.ui_theme_v1
(
    theme_code,
    theme_name_key,
    description_key,
    enabled,
    is_default,
    source_version
)
VALUES
(
    'DEFAULT',
    'ui.theme.default.name',
    'ui.theme.default.description',
    true,
    true,
    'MARKETCORE_UI_FRAMEWORK_THEME_REGISTRY_V1'
)
ON CONFLICT(theme_code)
DO NOTHING;

INSERT INTO presentation.ui_theme_property_v1
(
    theme_code,
    property_code,
    property_value,
    property_type,
    description_key,
    display_order,
    source_version
)
VALUES

('DEFAULT','CARD_RADIUS','18','INTEGER','ui.theme.property.card_radius',10,'MARKETCORE_UI_FRAMEWORK_THEME_REGISTRY_V1'),
('DEFAULT','CARD_PADDING','16','INTEGER','ui.theme.property.card_padding',20,'MARKETCORE_UI_FRAMEWORK_THEME_REGISTRY_V1'),
('DEFAULT','SECTION_GAP','12','INTEGER','ui.theme.property.section_gap',30,'MARKETCORE_UI_FRAMEWORK_THEME_REGISTRY_V1'),
('DEFAULT','TOUCH_SIZE','44','INTEGER','ui.theme.property.touch_size',40,'MARKETCORE_UI_FRAMEWORK_THEME_REGISTRY_V1'),

('DEFAULT','PRIMARY_COLOR','brand.primary','TOKEN','ui.theme.property.primary_color',100,'MARKETCORE_UI_FRAMEWORK_THEME_REGISTRY_V1'),
('DEFAULT','SUCCESS_COLOR','status.success','TOKEN','ui.theme.property.success_color',110,'MARKETCORE_UI_FRAMEWORK_THEME_REGISTRY_V1'),
('DEFAULT','WARNING_COLOR','status.warning','TOKEN','ui.theme.property.warning_color',120,'MARKETCORE_UI_FRAMEWORK_THEME_REGISTRY_V1'),
('DEFAULT','ERROR_COLOR','status.error','TOKEN','ui.theme.property.error_color',130,'MARKETCORE_UI_FRAMEWORK_THEME_REGISTRY_V1'),

('DEFAULT','TITLE_FONT','font.title','TOKEN','ui.theme.property.title_font',200,'MARKETCORE_UI_FRAMEWORK_THEME_REGISTRY_V1'),
('DEFAULT','BODY_FONT','font.body','TOKEN','ui.theme.property.body_font',210,'MARKETCORE_UI_FRAMEWORK_THEME_REGISTRY_V1')

ON CONFLICT(theme_code,property_code)
DO NOTHING;
