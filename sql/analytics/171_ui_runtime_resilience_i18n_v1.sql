BEGIN;

INSERT INTO presentation.ui_resource_v1
(resource_key,locale_code,caption,caption_short,caption_mobile,tooltip,icon,resource_group)
VALUES
('status.shadow_heartbeat_older_than_10_minutes','ru','Heartbeat Shadow устарел','Shadow устарел','Устарел','Shadow-наблюдатель не подтверждал работу более 10 минут','','status'),
('status.edge_search_executor_failed:discover_regime','ru','Ошибка определения режима','Ошибка режима','Ошибка','Исполнитель не завершил определение рыночного режима; цикл должен продолжиться с контрольной точки','','status'),
('workspace.drawer.title','ru','Управление','Управление','Меню','Разделы, проблемные задачи и основные действия','','workspace'),
('workspace.drawer.open','ru','Открыть управление','Открыть','Открыть','Показать панель управления','','workspace'),
('workspace.drawer.close','ru','Скрыть управление','Скрыть','Скрыть','Свернуть панель управления','','workspace'),
('workspace.drawer.back','ru','Назад','Назад','Назад','Вернуться к предыдущему разделу','','workspace'),
('workspace.drawer.home','ru','Домой','Домой','Домой','Перейти на главную страницу','','workspace')
,
('workspace.drawer.opportunities','ru','Возможности','Возможности','Успехи','Подтверждённые положительные результаты и доступные направления продвижения','','workspace'),
('workspace.drawer.confirmed','ru','Подтверждено','Подтверждено','PASS','Положительный результат подтверждён данными','','workspace')
ON CONFLICT(resource_key,locale_code) DO UPDATE SET
 caption=excluded.caption,caption_short=excluded.caption_short,
 caption_mobile=excluded.caption_mobile,tooltip=excluded.tooltip,
 icon=excluded.icon,resource_group=excluded.resource_group;

COMMIT;
