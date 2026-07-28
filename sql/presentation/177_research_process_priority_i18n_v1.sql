BEGIN;

INSERT INTO presentation.ui_resource_v1
(resource_key,locale_code,caption,caption_short,caption_mobile,tooltip,icon,resource_group)
VALUES
('research.audit.column.process','ru','Процесс','Процесс','Процесс','Тип системного процесса','','research'),
('research.domain.edge_search','ru','Поиск edge','Поиск edge','Поиск','Полный автономный цикл поиска и проверки edge','','research'),
('research.domain.edge_search.tooltip','ru','Полный автономный цикл поиска и проверки edge','Поиск edge','Поиск','Полный автономный цикл поиска и проверки edge','','research'),
('research.domain.research_refresh','ru','Обновление данных','Обновление','Данные','Обновление исследовательской очереди, источников и связей стадий','','research'),
('research.domain.research_refresh.tooltip','ru','Обновление исследовательской очереди, источников и связей стадий','Обновление данных','Данные','Обновление исследовательской очереди, источников и связей стадий','','research'),
('table.sort.hint','ru','Двойной клик — сортировать','Сортировать','Сортировать','Двойной клик по заголовку меняет направление сортировки','','workspace'),
('table.sort.ascending','ru','По возрастанию','По возрастанию','Возрастание','Таблица отсортирована по возрастанию','','workspace'),
('table.sort.descending','ru','По убыванию','По убыванию','Убывание','Таблица отсортирована по убыванию','','workspace'),
('column.operator.deadline','ru','Срок до','Срок до','Срок','Срок действия решения либо время получения фактического результата по Москве.','','column'),
('home.operator.next.automatic','ru','Система проверит','Автоматически','Авто','Оператору ничего запускать не нужно: система выполнит проверку по расписанию.','','operator_decision_v2'),
('home.operator.next.review_block','ru','Проверить блок','Проверить блок','Блок','Двойной клик открывает причины и ставит аудируемую перепроверку в очередь.','','operator_decision_v2')
ON CONFLICT(resource_key,locale_code) DO UPDATE SET
caption=excluded.caption,caption_short=excluded.caption_short,
caption_mobile=excluded.caption_mobile,tooltip=excluded.tooltip,
icon=excluded.icon,resource_group=excluded.resource_group;

COMMIT;
