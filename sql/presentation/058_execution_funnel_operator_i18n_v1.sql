INSERT INTO presentation.ui_resource_v1
(resource_key,locale_code,caption,caption_short,caption_mobile,tooltip,icon,resource_group)
VALUES
('column.positions_opened','ru','Открыты','Открыты','Откр.','','','workspace_v2_execution'),
('column.stops_placed','ru','Стоп установлен','Стоп','Стоп','','','workspace_v2_execution'),
('column.trailing_active','ru','Трейлинг активен','Активен','Акт.','','','workspace_v2_execution'),
('column.stops_improved','ru','Стоп улучшен','Улучшен','Ул.','','','workspace_v2_execution'),
('column.profit_locks','ru','Фиксация прибыли','Фиксация','Фикс.','','','workspace_v2_execution'),
('column.take_profits','ru','Тейк-профит','TP','TP','','','workspace_v2_execution'),
('column.positions_closed','ru','Закрыты','Закрыты','Закр.','','','workspace_v2_execution'),
('execution.funnel.execute_aria','ru','Открыть варианты управления исполнением','Управление исполнением','Управление','','','workspace_v2_execution'),
('execution.funnel.progress','ru','Анализ цепочки сопровождения позиции','Анализ сопровождения','Анализ','','','workspace_v2_execution'),
('execution.funnel.confirm_title','ru','Выберите действие для сопровождения','Действие сопровождения','Действие','','','workspace_v2_execution')
ON CONFLICT(resource_key,locale_code) DO UPDATE SET
 caption=excluded.caption,caption_short=excluded.caption_short,
 caption_mobile=excluded.caption_mobile,tooltip=excluded.tooltip,
 icon=excluded.icon,resource_group=excluded.resource_group;
