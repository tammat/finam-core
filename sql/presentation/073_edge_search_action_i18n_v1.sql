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

INSERT INTO presentation.ui_resource_v1
(resource_key,locale_code,caption,caption_short,caption_mobile,tooltip,icon,resource_group) VALUES
('research.algorithms.title','ru','Результаты алгоритмов','Алгоритмы','Алг.','Последний доверенный walk-forward','','research'),
('research.algorithm.column.algorithm','ru','Алгоритм','Алгоритм','Алг.','','','research'),
('research.algorithm.column.markets','ru','Рынки','Рынки','Рын.','','','research'),
('research.algorithm.column.variants','ru','Варианты','Варианты','Вар.','','','research'),
('research.algorithm.column.folds','ru','Фолды','Фолды','Фолд.','','','research'),
('research.algorithm.column.pf','ru','Лучший PF','PF','PF','','','research'),
('research.algorithm.column.passes','ru','PASS','PASS','PASS','','','research'),
('research.algorithm.column.status','ru','Статус','Статус','Стат.','','','research'),
('research.algorithm.column.reason','ru','Причина FAIL','Причина','Прич.','','','research'),
('research.algorithm.folds','ru','{passed}/{total}','{passed}/{total}','{passed}/{total}','','','research'),
('research.algorithm.status.pass','ru','Подтверждено','PASS','PASS','','','research'),
('research.algorithm.status.no_pass','ru','Нет PASS','Нет PASS','Нет','','','research')
ON CONFLICT(resource_key,locale_code) DO UPDATE SET caption=EXCLUDED.caption,caption_short=EXCLUDED.caption_short,caption_mobile=EXCLUDED.caption_mobile,tooltip=EXCLUDED.tooltip,icon=EXCLUDED.icon,resource_group=EXCLUDED.resource_group;

INSERT INTO presentation.ui_resource_v1 (
    resource_key,locale_code,caption,caption_short,caption_mobile,tooltip,icon,resource_group
) VALUES (
    'research.metric.edge_search_status','ru','Статус поиска edge','Статус поиска','Поиск',
    'Состояние последнего запуска полного конвейера поиска edge','','metric'
) ON CONFLICT (resource_key,locale_code) DO UPDATE SET
caption=EXCLUDED.caption,caption_short=EXCLUDED.caption_short,caption_mobile=EXCLUDED.caption_mobile,
tooltip=EXCLUDED.tooltip,icon=EXCLUDED.icon,resource_group=EXCLUDED.resource_group;
