BEGIN;

INSERT INTO presentation.ui_resource_v1
(resource_key,locale_code,caption,caption_short,caption_mobile,tooltip,icon,resource_group)
VALUES
('column.blocking_rule','ru','Блокирующее правило','Блокировка','Блок','Правило, остановившее переход сигнала к заявке','','column'),
('column.lost_signals','ru','Потерянные сигналы','Сигналов','Сигн.','Число уникальных сигналов, не дошедших до заявки','','column'),
('column.loss_share_pct','ru','Доля потерь, %','Доля, %','Доля','Доля этой причины среди всех блокировок текущего снимка','','column'),
('column.instruments','ru','Затронутые инструменты','Инструменты','Инстр.','Примеры инструментов, на которых сработало правило','','column'),
('column.next_action','ru','Следующее действие','Решение','Далее','Краткое действие системы для устранения или проверки блокировки','','column')
ON CONFLICT(resource_key,locale_code) DO UPDATE SET
 caption=excluded.caption,caption_short=excluded.caption_short,
 caption_mobile=excluded.caption_mobile,tooltip=excluded.tooltip,
 icon=excluded.icon,resource_group=excluded.resource_group;

COMMIT;
