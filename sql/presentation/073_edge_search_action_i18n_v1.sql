INSERT INTO presentation.ui_resource_v1 (
    resource_key,locale_code,caption,caption_short,caption_mobile,tooltip,icon,resource_group
) VALUES (
    'research.action.run_edge_search','ru','Запустить поиск edge','Поиск edge','Поиск',
    'Запустить полный безопасный поиск: regime, walk-forward, OOS и проверка допуска','▶','action'
) ON CONFLICT (resource_key,locale_code) DO UPDATE SET
caption=EXCLUDED.caption,caption_short=EXCLUDED.caption_short,caption_mobile=EXCLUDED.caption_mobile,
tooltip=EXCLUDED.tooltip,icon=EXCLUDED.icon,resource_group=EXCLUDED.resource_group;

INSERT INTO presentation.ui_resource_v1 (
    resource_key,locale_code,caption,caption_short,caption_mobile,tooltip,icon,resource_group
) VALUES
('research.metric.edge_search_step','ru','Этап поиска','Этап','Этап','Текущий этап конвейера','','metric'),
('research.metric.edge_search_progress','ru','Прогресс поиска','Прогресс','Прогр.','Процент завершения конвейера','','metric'),
('research.metric.edge_search_markets','ru','Проверено рынков','Рынки','Рынки','Количество фактически проверенных рынков','','metric'),
('research.metric.edge_search_combinations','ru','Проверено вариантов','Варианты','Варианты','Количество проверенных комбинаций','','metric'),
('research.metric.edge_search_pass','ru','Найдено OOS PASS','OOS PASS','PASS','Количество строгих OOS PASS','','metric')
ON CONFLICT (resource_key,locale_code) DO UPDATE SET
caption=EXCLUDED.caption,caption_short=EXCLUDED.caption_short,caption_mobile=EXCLUDED.caption_mobile,
tooltip=EXCLUDED.tooltip,icon=EXCLUDED.icon,resource_group=EXCLUDED.resource_group;

INSERT INTO presentation.ui_resource_v1 (
    resource_key,locale_code,caption,caption_short,caption_mobile,tooltip,icon,resource_group
) VALUES (
    'research.metric.edge_search_status','ru','Статус поиска edge','Статус поиска','Поиск',
    'Состояние последнего запуска полного конвейера поиска edge','','metric'
) ON CONFLICT (resource_key,locale_code) DO UPDATE SET
caption=EXCLUDED.caption,caption_short=EXCLUDED.caption_short,caption_mobile=EXCLUDED.caption_mobile,
tooltip=EXCLUDED.tooltip,icon=EXCLUDED.icon,resource_group=EXCLUDED.resource_group;
