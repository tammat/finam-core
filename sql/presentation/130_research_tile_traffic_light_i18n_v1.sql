INSERT INTO presentation.ui_resource_v1
(resource_key,locale_code,caption,caption_short,caption_mobile,tooltip,icon,resource_group) VALUES
('research.tile.status.ready','ru','Готово','Готово','Готово','Данные готовы к использованию.','','research'),
('research.tile.status.attention','ru','Внимание','Внимание','Вним.','Показатель требует внимания.','','research'),
('research.tile.status.blocked','ru','Блок','Блок','Блок','Продвижение заблокировано.','','research'),
('research.tile.status.found','ru','Найдены','Найдены','Есть','Кандидаты найдены и сохранены.','','research'),
('research.tile.status.pass','ru','Есть PASS','PASS','PASS','Есть кандидаты, прошедшие OOS-проверку.','','research'),
('research.tile.status.no_pass','ru','Нет PASS','Нет PASS','Нет','Ни один кандидат пока не прошёл OOS-проверку.','','research'),
('research.tile.status.empty','ru','Пусто','Пусто','Пусто','Записей для этого показателя сейчас нет.','','research'),
('research.tile.status.queue','ru','Очередь','Очередь','Очередь','Заявки ожидают выполнения системой.','','research'),
('research.tile.status.running','ru','В работе','В работе','Работа','Системный процесс ещё выполняется.','','research')
ON CONFLICT(resource_key,locale_code) DO UPDATE SET
 caption=EXCLUDED.caption,caption_short=EXCLUDED.caption_short,caption_mobile=EXCLUDED.caption_mobile,
 tooltip=EXCLUDED.tooltip,icon=EXCLUDED.icon,resource_group=EXCLUDED.resource_group;

INSERT INTO presentation.ui_resource_v1
(resource_key,locale_code,caption,caption_short,caption_mobile,tooltip,icon,resource_group)
SELECT resource_key || '.tooltip', locale_code, tooltip, tooltip, tooltip, tooltip, icon, resource_group
FROM presentation.ui_resource_v1
WHERE locale_code='ru' AND resource_key LIKE 'research.tile.status.%'
  AND resource_key NOT LIKE '%.tooltip'
ON CONFLICT(resource_key,locale_code) DO UPDATE SET
 caption=EXCLUDED.caption,caption_short=EXCLUDED.caption_short,caption_mobile=EXCLUDED.caption_mobile,
 tooltip=EXCLUDED.tooltip,icon=EXCLUDED.icon,resource_group=EXCLUDED.resource_group;
