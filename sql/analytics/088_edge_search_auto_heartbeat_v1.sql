ALTER TABLE analytics.edge_search_auto_schedule_state_v1
ADD COLUMN IF NOT EXISTS last_error_code text;

INSERT INTO presentation.ui_resource_v1
(resource_key,locale_code,caption,caption_short,caption_mobile,tooltip,icon,resource_group) VALUES
('research.tile.auto_status','ru','Состояние автопоиска','Автостатус','Авто',
 'Heartbeat системного планировщика поиска edge','','research'),
('research.domain.never_run','ru','Ожидает запуска','Ожидает','Ждёт',
 'Планировщик ещё не достиг первого разрешённого окна','','research'),
('research.domain.never_run.tooltip','ru','Первый запуск ожидается в разрешённое окно','Ожидается','Ждёт',
 'Первый запуск ожидается в разрешённое окно','','research'),
('research.domain.healthy','ru','Работает','Работает','OK',
 'Планировщик успешно выполнил последнюю проверку','','research'),
('research.domain.healthy.tooltip','ru','Последняя проверка автопоиска выполнена успешно','Работает','OK',
 'Последняя проверка автопоиска выполнена успешно','','research')
ON CONFLICT(resource_key,locale_code) DO UPDATE SET
caption=EXCLUDED.caption,caption_short=EXCLUDED.caption_short,caption_mobile=EXCLUDED.caption_mobile,
tooltip=EXCLUDED.tooltip,icon=EXCLUDED.icon,resource_group=EXCLUDED.resource_group;
