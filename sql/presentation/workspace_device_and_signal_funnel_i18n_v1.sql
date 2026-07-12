INSERT INTO presentation.ui_theme_v1
(theme_code, theme_name_key, description_key, enabled, is_default, source_version)
VALUES
('TABLET','ui.theme.tablet.name','ui.theme.tablet.description',true,false,'WORKSPACE_DEVICE_AND_SIGNAL_FUNNEL_I18N_V1')
ON CONFLICT(theme_code) DO UPDATE SET
  theme_name_key=EXCLUDED.theme_name_key,
  description_key=EXCLUDED.description_key,
  enabled=EXCLUDED.enabled,
  source_version=EXCLUDED.source_version,
  updated_at=now();

INSERT INTO presentation.ui_theme_property_v1
(theme_code, property_code, property_value, property_type, description_key, display_order, source_version)
VALUES
('TABLET','SHELL_MAX_WIDTH','1024','INTEGER','ui.theme.property.shell_max_width',300,'WORKSPACE_DEVICE_AND_SIGNAL_FUNNEL_I18N_V1'),
('TABLET','SHELL_PADDING','10','INTEGER','ui.theme.property.shell_padding',310,'WORKSPACE_DEVICE_AND_SIGNAL_FUNNEL_I18N_V1'),
('TABLET','GRID_MIN_CARD_WIDTH','320','INTEGER','ui.theme.property.grid_min_card_width',320,'WORKSPACE_DEVICE_AND_SIGNAL_FUNNEL_I18N_V1'),
('TABLET','GRID_GAP','10','INTEGER','ui.theme.property.grid_gap',330,'WORKSPACE_DEVICE_AND_SIGNAL_FUNNEL_I18N_V1'),
('TABLET','CARD_RADIUS','16','INTEGER','ui.theme.property.card_radius',340,'WORKSPACE_DEVICE_AND_SIGNAL_FUNNEL_I18N_V1'),
('TABLET','CARD_PADDING','12','INTEGER','ui.theme.property.card_padding',350,'WORKSPACE_DEVICE_AND_SIGNAL_FUNNEL_I18N_V1'),
('TABLET','VALUE_ROW_GAP','8','INTEGER','ui.theme.property.value_row_gap',360,'WORKSPACE_DEVICE_AND_SIGNAL_FUNNEL_I18N_V1'),
('TABLET','VALUE_ROW_LAYOUT','INLINE','TEXT','ui.theme.property.value_row_layout',370,'WORKSPACE_DEVICE_AND_SIGNAL_FUNNEL_I18N_V1')
ON CONFLICT(theme_code, property_code) DO UPDATE SET
  property_value=EXCLUDED.property_value,
  property_type=EXCLUDED.property_type,
  description_key=EXCLUDED.description_key,
  display_order=EXCLUDED.display_order,
  source_version=EXCLUDED.source_version,
  updated_at=now();

INSERT INTO presentation.ui_resource_v1
(resource_key, locale_code, caption, caption_short, caption_mobile, tooltip, resource_group, source_version)
VALUES
('home.card.portfolio.tablet.title','ru','Портфель · планшет','Портфель','Портфель','Планшетный профиль портфеля','workspace','WORKSPACE_DEVICE_AND_SIGNAL_FUNNEL_I18N_V1'),
('ui.theme.tablet.name','ru','Планшет','Планшет','Планшет','Планшетная тема','theme','WORKSPACE_DEVICE_AND_SIGNAL_FUNNEL_I18N_V1'),
('ui.theme.tablet.description','ru','Планшетный интерфейс MarketCore','Планшет','Планшет','Планшетный интерфейс MarketCore','theme','WORKSPACE_DEVICE_AND_SIGNAL_FUNNEL_I18N_V1'),
('control_center.signal_funnel.reason.data.label','ru','Данные','Данные','Данные','','signal_funnel','WORKSPACE_DEVICE_AND_SIGNAL_FUNNEL_I18N_V1'),
('control_center.signal_funnel.reason.data.action','ru','Восстановить историю и свежесть, затем пройти контроль качества данных','Восстановить данные','Восстановить данные','','signal_funnel','WORKSPACE_DEVICE_AND_SIGNAL_FUNNEL_I18N_V1'),
('control_center.signal_funnel.reason.volatility.label','ru','Волатильность','Волатильность','Волатильность','','signal_funnel','WORKSPACE_DEVICE_AND_SIGNAL_FUNNEL_I18N_V1'),
('control_center.signal_funnel.reason.volatility.action','ru','Настроить пороги волатильности отдельно для режима и сессии','Настроить пороги','Настроить пороги','','signal_funnel','WORKSPACE_DEVICE_AND_SIGNAL_FUNNEL_I18N_V1'),
('control_center.signal_funnel.reason.liquidity.label','ru','Ликвидность','Ликвидность','Ликвидность','','signal_funnel','WORKSPACE_DEVICE_AND_SIGNAL_FUNNEL_I18N_V1'),
('control_center.signal_funnel.reason.liquidity.action','ru','Проверить спред, объём, проскальзывание и допустимые часы входа','Проверить ликвидность','Проверить ликвидность','','signal_funnel','WORKSPACE_DEVICE_AND_SIGNAL_FUNNEL_I18N_V1'),
('control_center.signal_funnel.reason.risk.label','ru','Риск','Риск','Риск','','signal_funnel','WORKSPACE_DEVICE_AND_SIGNAL_FUNNEL_I18N_V1'),
('control_center.signal_funnel.reason.risk.action','ru','Снизить размер, концентрацию или факторную экспозицию','Снизить риск','Снизить риск','','signal_funnel','WORKSPACE_DEVICE_AND_SIGNAL_FUNNEL_I18N_V1'),
('control_center.signal_funnel.reason.edge.label','ru','Edge','Edge','Edge','','signal_funnel','WORKSPACE_DEVICE_AND_SIGNAL_FUNNEL_I18N_V1'),
('control_center.signal_funnel.reason.edge.action','ru','Оставить в исследовании, расширить гипотезу и повторить OOS','Повторить OOS','Повторить OOS','','signal_funnel','WORKSPACE_DEVICE_AND_SIGNAL_FUNNEL_I18N_V1'),
('control_center.signal_funnel.reason.market.label','ru','Рынок и сессия','Рынок','Рынок','','signal_funnel','WORKSPACE_DEVICE_AND_SIGNAL_FUNNEL_I18N_V1'),
('control_center.signal_funnel.reason.market.action','ru','Ограничить допустимые режимы рынка и торговые сессии','Уточнить режим','Уточнить режим','','signal_funnel','WORKSPACE_DEVICE_AND_SIGNAL_FUNNEL_I18N_V1'),
('control_center.signal_funnel.reason.exit.label','ru','Выход','Выход','Выход','','signal_funnel','WORKSPACE_DEVICE_AND_SIGNAL_FUNNEL_I18N_V1'),
('control_center.signal_funnel.reason.exit.action','ru','Сравнить политики выхода, время удержания и защитные условия','Проверить выход','Проверить выход','','signal_funnel','WORKSPACE_DEVICE_AND_SIGNAL_FUNNEL_I18N_V1'),
('control_center.signal_funnel.reason.setup.label','ru','Сетап сигнала','Сетап','Сетап','','signal_funnel','WORKSPACE_DEVICE_AND_SIGNAL_FUNNEL_I18N_V1'),
('control_center.signal_funnel.reason.setup.action','ru','Разделить типы сетапов и проверить каждый в режиме и сессии','Разделить сетапы','Разделить сетапы','','signal_funnel','WORKSPACE_DEVICE_AND_SIGNAL_FUNNEL_I18N_V1'),
('control_center.signal_funnel.reason.execution.label','ru','Исполнение','Исполнение','Исполнение','','signal_funnel','WORKSPACE_DEVICE_AND_SIGNAL_FUNNEL_I18N_V1'),
('control_center.signal_funnel.reason.execution.action','ru','Проверить сверку брокера, заявок, сделок и маршрутизацию','Проверить исполнение','Проверить исполнение','','signal_funnel','WORKSPACE_DEVICE_AND_SIGNAL_FUNNEL_I18N_V1'),
('control_center.signal_funnel.reason.research.label','ru','Исследование','Исследование','Исследование','','signal_funnel','WORKSPACE_DEVICE_AND_SIGNAL_FUNNEL_I18N_V1'),
('control_center.signal_funnel.reason.research.action','ru','Завершить проверку исследования и определить критерий продвижения','Завершить проверку','Завершить проверку','','signal_funnel','WORKSPACE_DEVICE_AND_SIGNAL_FUNNEL_I18N_V1'),
('control_center.signal_funnel.reason.lifecycle.label','ru','Жизненный цикл','Цикл','Цикл','','signal_funnel','WORKSPACE_DEVICE_AND_SIGNAL_FUNNEL_I18N_V1'),
('control_center.signal_funnel.reason.lifecycle.action','ru','Разделить активные, архивные, тестовые и ожидающие состояния','Уточнить состояние','Уточнить состояние','','signal_funnel','WORKSPACE_DEVICE_AND_SIGNAL_FUNNEL_I18N_V1'),
('control_center.signal_funnel.reason.block.label','ru','Блокировка','Блокировка','Блокировка','','signal_funnel','WORKSPACE_DEVICE_AND_SIGNAL_FUNNEL_I18N_V1'),
('control_center.signal_funnel.reason.block.action','ru','Открыть управляющий шлюз и устранить конкретную блокировку','Снять блокировку','Снять блокировку','','signal_funnel','WORKSPACE_DEVICE_AND_SIGNAL_FUNNEL_I18N_V1'),
('control_center.signal_funnel.reason.pass.label','ru','Пройдено','Пройдено','Пройдено','','signal_funnel','WORKSPACE_DEVICE_AND_SIGNAL_FUNNEL_I18N_V1'),
('control_center.signal_funnel.reason.pass.action','ru','Наблюдать стабильность и не менять правила без нового OOS','Наблюдать','Наблюдать','','signal_funnel','WORKSPACE_DEVICE_AND_SIGNAL_FUNNEL_I18N_V1'),
('control_center.signal_funnel.reason.quality.label','ru','Качество модели','Качество','Качество','','signal_funnel','WORKSPACE_DEVICE_AND_SIGNAL_FUNNEL_I18N_V1'),
('control_center.signal_funnel.reason.quality.action','ru','Проверить нестабильность, шум и отсутствие измеримого эффекта','Проверить качество','Проверить качество','','signal_funnel','WORKSPACE_DEVICE_AND_SIGNAL_FUNNEL_I18N_V1'),
('control_center.signal_funnel.reason.unknown.label','ru','Не определено','Не определено','Не определено','','signal_funnel','WORKSPACE_DEVICE_AND_SIGNAL_FUNNEL_I18N_V1'),
('control_center.signal_funnel.reason.unknown.action','ru','Исправить источник: пустые, неизвестные и числовые причины недопустимы','Исправить источник','Исправить источник','','signal_funnel','WORKSPACE_DEVICE_AND_SIGNAL_FUNNEL_I18N_V1'),
('control_center.signal_funnel.reason.other.label','ru','Неклассифицировано','Прочее','Прочее','','signal_funnel','WORKSPACE_DEVICE_AND_SIGNAL_FUNNEL_I18N_V1'),
('control_center.signal_funnel.reason.other.action','ru','Провести аудит происхождения и добавить точное правило классификации','Классифицировать','Классифицировать','','signal_funnel','WORKSPACE_DEVICE_AND_SIGNAL_FUNNEL_I18N_V1')
ON CONFLICT(resource_key, locale_code) DO UPDATE SET
  caption=EXCLUDED.caption,
  caption_short=EXCLUDED.caption_short,
  caption_mobile=EXCLUDED.caption_mobile,
  tooltip=EXCLUDED.tooltip,
  resource_group=EXCLUDED.resource_group,
  source_version=EXCLUDED.source_version,
  updated_at=now();
