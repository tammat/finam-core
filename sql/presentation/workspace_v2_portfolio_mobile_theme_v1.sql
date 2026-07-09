INSERT INTO presentation.ui_theme_v1
(theme_code, theme_name_key, description_key, enabled, is_default, source_version)
VALUES
('PHONE','ui.theme.phone.name','ui.theme.phone.description',true,false,'WORKSPACE_V2_PORTFOLIO_MOBILE_THEME_V1')
ON CONFLICT(theme_code)
DO UPDATE SET
  theme_name_key=EXCLUDED.theme_name_key,
  description_key=EXCLUDED.description_key,
  enabled=EXCLUDED.enabled,
  is_default=EXCLUDED.is_default,
  source_version=EXCLUDED.source_version,
  updated_at=now();

INSERT INTO presentation.ui_theme_property_v1
(theme_code, property_code, property_value, property_type, description_key, display_order, source_version)
VALUES
('PHONE','SHELL_MAX_WIDTH','480','INTEGER','ui.theme.property.shell_max_width',300,'WORKSPACE_V2_PORTFOLIO_MOBILE_THEME_V1'),
('PHONE','SHELL_PADDING','8','INTEGER','ui.theme.property.shell_padding',310,'WORKSPACE_V2_PORTFOLIO_MOBILE_THEME_V1'),
('PHONE','GRID_MIN_CARD_WIDTH','280','INTEGER','ui.theme.property.grid_min_card_width',320,'WORKSPACE_V2_PORTFOLIO_MOBILE_THEME_V1'),
('PHONE','GRID_GAP','8','INTEGER','ui.theme.property.grid_gap',330,'WORKSPACE_V2_PORTFOLIO_MOBILE_THEME_V1'),
('PHONE','CARD_RADIUS','14','INTEGER','ui.theme.property.card_radius',340,'WORKSPACE_V2_PORTFOLIO_MOBILE_THEME_V1'),
('PHONE','CARD_PADDING','10','INTEGER','ui.theme.property.card_padding',350,'WORKSPACE_V2_PORTFOLIO_MOBILE_THEME_V1'),
('PHONE','VALUE_ROW_GAP','4','INTEGER','ui.theme.property.value_row_gap',360,'WORKSPACE_V2_PORTFOLIO_MOBILE_THEME_V1'),
('PHONE','VALUE_ROW_LAYOUT','STACKED','TEXT','ui.theme.property.value_row_layout',370,'WORKSPACE_V2_PORTFOLIO_MOBILE_THEME_V1')
ON CONFLICT(theme_code, property_code)
DO UPDATE SET
  property_value=EXCLUDED.property_value,
  property_type=EXCLUDED.property_type,
  description_key=EXCLUDED.description_key,
  display_order=EXCLUDED.display_order,
  source_version=EXCLUDED.source_version,
  updated_at=now();
