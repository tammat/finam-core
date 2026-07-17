INSERT INTO presentation.ui_resource_v1
(resource_key,locale_code,caption,caption_short,caption_mobile,tooltip,icon,resource_group) VALUES
('research.audit.title','ru','Системные циклы поиска','Циклы поиска','Циклы','История автономных запусков и их результатов','','research'),
('research.audit.column.started','ru','Запуск','Запуск','Время','','','research'),
('research.audit.column.status','ru','Статус','Статус','Стат.','','','research'),
('research.audit.column.steps','ru','Этапы','Этапы','Этап.','','','research'),
('research.audit.column.duration','ru','Сек.','Сек.','Сек.','','','research'),
('research.audit.column.outcome','ru','Результат','Итог','Итог','','','research'),
('research.audit.column.reason','ru','Причина','Причина','Прич.','','','research'),
('research.audit.column.recommendation','ru','Далее','Далее','Далее','','','research'),
('research.audit.column.analysis','ru','Анализ','Анализ','Анализ','','','research'),
('research.audit.steps','ru','{completed}/{total}','{completed}/{total}','{completed}/{total}','','','research'),
('research.audit.row.tooltip','ru','{explanation}','{explanation}','{explanation}','','','research')
ON CONFLICT(resource_key,locale_code) DO UPDATE SET
 caption=EXCLUDED.caption,caption_short=EXCLUDED.caption_short,caption_mobile=EXCLUDED.caption_mobile,
 tooltip=EXCLUDED.tooltip,icon=EXCLUDED.icon,resource_group=EXCLUDED.resource_group;
