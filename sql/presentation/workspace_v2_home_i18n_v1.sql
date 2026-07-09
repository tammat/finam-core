INSERT INTO presentation.ui_resource_v1
(resource_key, locale_code, caption, caption_short, caption_mobile, tooltip, icon, resource_group)
VALUES
('home.workspace.title','ru','MarketCore OS','MarketCore OS','MC OS','Главный рабочий стол MarketCore OS','', 'workspace_v2_home'),
('home.workspace.subtitle','ru','Рабочий стол оператора','Рабочий стол','Главная','Сводка состояния системы','', 'workspace_v2_home'),

('home.section.system.title','ru','Состояние системы','Система','Сист.','Общее состояние MarketCore OS','', 'workspace_v2_home'),
('home.section.system.subtitle','ru','Контроль готовности','Готовность','Гот.','Ключевые признаки готовности системы','', 'workspace_v2_home'),

('home.section.navigation.title','ru','Разделы','Разделы','Разд.','Основные рабочие разделы','', 'workspace_v2_home'),
('home.section.navigation.subtitle','ru','Переход к рабочим экранам','Переходы','Нав.','Навигация по Workspace V2','', 'workspace_v2_home'),

('home.card.portfolio.title','ru','Портфель','Портфель','Портф.','Капитал, позиции и риск','', 'workspace_v2_home'),
('home.card.probe.title','ru','Проба','Проба','Проба','Тестовая проверка без реальных заявок','', 'workspace_v2_home'),
('home.card.research.title','ru','Исследование','Исследование','Исслед.','Поиск и проверка рыночных гипотез','', 'workspace_v2_home'),
('home.card.runtime.title','ru','Runtime','Runtime','Run','Текущий контур исполнения и наблюдения','', 'workspace_v2_home'),

('home.card.system.status.title','ru','Этап','Этап','Этап','Текущий этап жизненного цикла','', 'workspace_v2_home'),
('home.card.system.status.subtitle','ru','Исследование','Исслед.','Исслед.','Рабочий режим пока не разрешен','', 'workspace_v2_home')
ON CONFLICT(resource_key, locale_code)
DO UPDATE SET
  caption=EXCLUDED.caption,
  caption_short=EXCLUDED.caption_short,
  caption_mobile=EXCLUDED.caption_mobile,
  tooltip=EXCLUDED.tooltip,
  icon=EXCLUDED.icon,
  resource_group=EXCLUDED.resource_group;
