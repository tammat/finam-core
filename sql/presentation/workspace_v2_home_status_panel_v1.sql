INSERT INTO presentation.ui_resource_v1
(resource_key, locale_code, caption, caption_short, caption_mobile, tooltip, icon, resource_group)
VALUES
('home.section.status.title','ru','Панель состояния','Состояние','Статус','Ключевые контуры MarketCore OS','', 'workspace_v2_home'),
('home.section.status.subtitle','ru','Быстрый контроль готовности','Контроль','Контр.','Сводка по основным рабочим контурам','', 'workspace_v2_home'),

('home.card.status.system.title','ru','Система','Система','Сист.','Состояние UI Shell и Workspace','', 'workspace_v2_home'),
('home.card.status.portfolio.title','ru','Портфель','Портфель','Портф.','Портфельный экран и данные позиций','', 'workspace_v2_home'),
('home.card.status.research.title','ru','Исследование','Исследование','Иссл.','Контур поиска и проверки гипотез','', 'workspace_v2_home'),
('home.card.status.probe.title','ru','Проба','Проба','Проба','Тестовая проверка без реальных заявок','', 'workspace_v2_home'),
('home.card.status.observation.title','ru','Наблюдение','Наблюд.','Набл.','Реальный рынок без исполнения заявок','', 'workspace_v2_home'),
('home.card.status.runtime.title','ru','Runtime','Runtime','Run','Рабочий контур исполнения и наблюдения','', 'workspace_v2_home'),

('home.card.status.ready.subtitle','ru','Доступно','Доступно','Да','Контур доступен','', 'workspace_v2_home'),
('home.card.status.pending.subtitle','ru','В работе','В работе','Раб.','Контур еще дорабатывается','', 'workspace_v2_home'),
('home.card.status.blocked.subtitle','ru','Заблокировано','Блок','Блок','Контур заблокирован правилами допуска','', 'workspace_v2_home')
ON CONFLICT(resource_key, locale_code)
DO UPDATE SET
  caption=EXCLUDED.caption,
  caption_short=EXCLUDED.caption_short,
  caption_mobile=EXCLUDED.caption_mobile,
  tooltip=EXCLUDED.tooltip,
  icon=EXCLUDED.icon,
  resource_group=EXCLUDED.resource_group;
