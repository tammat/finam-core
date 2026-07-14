INSERT INTO presentation.ui_theme_property_v1(
 theme_code,property_code,property_value,property_type,description_key,display_order,source_version
) VALUES
('DEFAULT','HOME_STATUS_CARD_MIN_HEIGHT','92','INTEGER','ui.theme.property.home_status_card_min_height',510,'HOME_STATUS_COMPACT_DECISION_V1'),
('DEFAULT','HOME_STATUS_CARD_PADDING','12','INTEGER','ui.theme.property.home_status_card_padding',520,'HOME_STATUS_COMPACT_DECISION_V1'),
('DEFAULT','HOME_STATUS_KPI_FONT_SIZE','15','INTEGER','ui.theme.property.home_status_kpi_font_size',530,'HOME_STATUS_COMPACT_DECISION_V1'),
('DEFAULT','HOME_STATUS_KPI_FONT_WEIGHT','600','INTEGER','ui.theme.property.home_status_kpi_font_weight',540,'HOME_STATUS_COMPACT_DECISION_V1')
ON CONFLICT(theme_code,property_code) DO UPDATE SET property_value=EXCLUDED.property_value,property_type=EXCLUDED.property_type,description_key=EXCLUDED.description_key,display_order=EXCLUDED.display_order,source_version=EXCLUDED.source_version,updated_at=now();

INSERT INTO presentation.ui_resource_v1(resource_key,locale_code,caption,caption_short,caption_mobile,tooltip,icon,resource_group) VALUES
('home.decision.progress','ru','Подготовка вариантов решения','Подготовка','Подготовка','','','workspace_v2_home'),
('home.decision.progress_complete','ru','Варианты готовы','Готово','Готово','','','workspace_v2_home'),
('home.decision.title','ru','Выберите действие оператора','Выберите действие','Действие','','','workspace_v2_home'),
('home.decision.confirm','ru','Подтвердить выбор','Подтвердить','Подтвердить','','','workspace_v2_home'),
('home.decision.open_section','ru','Открыть соответствующий раздел анализа','Открыть анализ','Открыть','','','workspace_v2_home'),
('home.decision.keep_observing','ru','Оставить без изменений и продолжить наблюдение','Продолжить наблюдение','Наблюдать','','','workspace_v2_home')
ON CONFLICT(resource_key,locale_code) DO UPDATE SET caption=EXCLUDED.caption,caption_short=EXCLUDED.caption_short,caption_mobile=EXCLUDED.caption_mobile,tooltip=EXCLUDED.tooltip,icon=EXCLUDED.icon,resource_group=EXCLUDED.resource_group;
