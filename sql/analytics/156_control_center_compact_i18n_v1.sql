BEGIN;

INSERT INTO presentation.ui_resource_v1
(resource_key,locale_code,caption,caption_short,caption_mobile,tooltip,icon,resource_group)
VALUES
('column.best.bid','ru','Лучшая цена покупки','Bid','Bid','Реальная лучшая цена покупки','','column'),
('column.best.ask','ru','Лучшая цена продажи','Ask','Ask','Реальная лучшая цена продажи','','column'),
('column.bid.depth','ru','Объём лучшей покупки','Объём bid','Bid','Реальный объём верхнего уровня покупки; число уровней показывается отдельно','','column'),
('column.ask.depth','ru','Объём лучшей продажи','Объём ask','Ask','Реальный объём верхнего уровня продажи; число уровней показывается отдельно','','column'),
('column.exchange.ts','ru','Биржевое время','Время биржи','Время','Метка времени биржевого источника','','column'),
('column.microstructure.coverage.pct','ru','Покрытие стаканом, %','Покрытие','Покр.','Доля сделок с подтверждёнными входом и выходом','','column'),
('column.microstructure.matched.trades','ru','Подтверждённые сделки','Подтв.','Подтв.','Сделки с реальными котировками входа и выхода','','column'),
('column.eligible.oos.trades','ru','Доступные OOS-сделки','OOS всего','OOS','Сделки до проверки микроструктуры','','column'),
('column.microstructure.start','ru','Начало подтверждения','Начало','Нач.','Начало независимой микроструктурной выборки','','column'),
('column.microstructure.end','ru','Конец подтверждения','Конец','Кон.','Конец независимой микроструктурной выборки','','column'),
('column.blocking.rule','ru','Блокирующее правило','Блокировка','Блок','Правило, остановившее сигнал','','column'),
('column.lost.signals','ru','Потерянные сигналы','Сигналов','Сигн.','Уникальные сигналы, не дошедшие до заявки','','column'),
('column.loss.share.pct','ru','Доля потерь, %','Доля, %','Доля','Доля причины среди блокировок','','column'),
('column.next.action','ru','Следующее действие','Решение','Далее','Безопасное действие для проверки ограничения','','column'),
('column.detail','ru','Пояснение','Почему','Почему','Причина состояния текущего этапа','','column'),
('status.not_started','ru','Этап ещё не начат','Не начато','Не нач.','Предыдущий обязательный этап не дал входных объектов','','status')
ON CONFLICT(resource_key,locale_code) DO UPDATE SET
 caption=excluded.caption,caption_short=excluded.caption_short,
 caption_mobile=excluded.caption_mobile,tooltip=excluded.tooltip,
 icon=excluded.icon,resource_group=excluded.resource_group;

COMMIT;
