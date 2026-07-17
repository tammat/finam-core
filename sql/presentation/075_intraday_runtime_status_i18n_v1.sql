INSERT INTO presentation.ui_resource_v1
(resource_key,locale_code,caption,caption_short,caption_mobile,tooltip,icon,resource_group) VALUES
('status.waiting_admission','ru','Ожидается допуск стратегии','Ожидается допуск','Допуск','Модельные сделки начнутся только после подтверждённого допуска.','','status'),
('status.waiting_signals','ru','Ожидаются новые сигналы','Ожидаются сигналы','Сигналы','Стратегия допущена, но новых сигналов пока нет.','','status'),
('status.observing','ru','Идёт наблюдение','Наблюдение','Наблюдение','Система собирает результаты без реального исполнения.','','status'),
('status.waiting_candidate','ru','Ожидается подтверждённый кандидат','Ожидается кандидат','Кандидат','Теневое наблюдение начнётся после допуска кандидата.','','status'),
('status.stale','ru','Данные устарели','Устарело','Устарело','Источник давно не создавал новых событий.','','status'),
('intraday.metric.shadow_status','ru','Состояние теневого режима','Состояние','Статус','','','intraday')
ON CONFLICT(resource_key,locale_code) DO UPDATE SET
caption=EXCLUDED.caption,caption_short=EXCLUDED.caption_short,
caption_mobile=EXCLUDED.caption_mobile,tooltip=EXCLUDED.tooltip,
icon=EXCLUDED.icon,resource_group=EXCLUDED.resource_group;
