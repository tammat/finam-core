INSERT INTO presentation.ui_theme_property_v1
(theme_code, property_code, property_value, property_type, description_key, display_order, source_version)
VALUES
('DEFAULT','SHELL_MAX_WIDTH','1600','INTEGER','ui.theme.property.shell_max_width',300,'WORKSPACE_V2_THEME_APPLY_V1'),
('DEFAULT','SHELL_PADDING','12','INTEGER','ui.theme.property.shell_padding',310,'WORKSPACE_V2_THEME_APPLY_V1'),
('DEFAULT','GRID_MIN_CARD_WIDTH','340','INTEGER','ui.theme.property.grid_min_card_width',320,'WORKSPACE_V2_THEME_APPLY_V1'),
('DEFAULT','GRID_GAP','12','INTEGER','ui.theme.property.grid_gap',330,'WORKSPACE_V2_THEME_APPLY_V1'),
('DEFAULT','CARD_RADIUS','18','INTEGER','ui.theme.property.card_radius',340,'WORKSPACE_V2_THEME_APPLY_V1'),
('DEFAULT','CARD_PADDING','14','INTEGER','ui.theme.property.card_padding',350,'WORKSPACE_V2_THEME_APPLY_V1'),
('DEFAULT','VALUE_ROW_GAP','8','INTEGER','ui.theme.property.value_row_gap',360,'WORKSPACE_V2_THEME_APPLY_V1')
ON CONFLICT(theme_code, property_code)
DO UPDATE SET
  property_value=EXCLUDED.property_value,
  property_type=EXCLUDED.property_type,
  description_key=EXCLUDED.description_key,
  display_order=EXCLUDED.display_order,
  source_version=EXCLUDED.source_version,
  updated_at=now();
