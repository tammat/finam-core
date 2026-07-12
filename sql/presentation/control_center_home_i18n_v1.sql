INSERT INTO presentation.ui_resource_v1
(resource_key, locale_code, caption, caption_short, caption_mobile, tooltip, resource_group, source_version)
VALUES
('home.card.control_center.title','ru','Control Center','Центр управления','Управление','Открыть центр управления MarketCore','workspace','CONTROL_CENTER_HOME_I18N_V1'),
('control_center.action.generate_hypotheses','ru','Сгенерировать гипотезы','Генерировать','Генерировать','Создать и первично оценить новые комбинации стратегии, инструмента, режима и параметров','control_center','CONTROL_CENTER_HOME_I18N_V1'),
('control_center.action.validate_hypotheses','ru','Подготовить данные и проверить','Проверить','Проверить','Построить исторические режимы, пройти Data Quality Gate и повторить OOS','control_center','CONTROL_CENTER_HOME_I18N_V1'),
('control_center.action.running','ru','Запускаю…','Запускаю…','Запускаю…','Действие принято и запускается','control_center','CONTROL_CENTER_HOME_I18N_V1')
ON CONFLICT(resource_key, locale_code) DO UPDATE SET
  caption=EXCLUDED.caption,
  caption_short=EXCLUDED.caption_short,
  caption_mobile=EXCLUDED.caption_mobile,
  tooltip=EXCLUDED.tooltip,
  resource_group=EXCLUDED.resource_group,
  source_version=EXCLUDED.source_version,
  updated_at=now();
