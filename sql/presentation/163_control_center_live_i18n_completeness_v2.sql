BEGIN;

INSERT INTO presentation.ui_resource_v1
(resource_key,locale_code,caption,caption_short,caption_mobile,tooltip,icon,resource_group)
VALUES
('column.analysis.status','ru','Статус анализа','Анализ','Анализ','Текущее состояние анализа результата','','column'),
('column.detail.status','ru','Статус детализации','Детали','Детали','Текущее состояние подробного результата','','column'),
('column.fills.1h','ru','Исполнено за час','Сделки/ч','Сделки','Количество исполненных модельных сделок за последний час','','column'),
('column.last.quote.at','ru','Последняя котировка','Котировка','Котир.','Биржевое время последней полученной котировки','','column'),
('column.priority.rank','ru','Место приоритета','Место','№','Позиция объекта в автономной очереди','','column'),
('column.priority.score','ru','Оценка приоритета','Приоритет','Балл','Расчётная ценность следующего исследования','','column'),
('column.waiting.candidates','ru','Ожидают данных','Ожидают','Ждут','Количество кандидатов, ожидающих будущих данных','','column'),
('status.analysis','ru','Анализ','Анализ','Анализ','Этап анализа результата','','status'),
('status.detail','ru','Детали','Детали','Детали','Подробное состояние результата','','status'),
('status.donchian_volatility_breakout_v1','ru','Пробой Дончиана','Дончиан','Пробой','Пробой канала Дончиана с фильтром волатильности','','status'),
('status.microstructure_verified','ru','Стакан подтверждён','Стакан готов','Готово','Bid/ask, глубина стакана и биржевая метка времени подтверждены','','status'),
('status.reserve','ru','Резерв','Резерв','Резерв','Объект сохранён в резерве для следующего цикла','','status')
ON CONFLICT(resource_key,locale_code) DO UPDATE SET
 caption=excluded.caption,caption_short=excluded.caption_short,
 caption_mobile=excluded.caption_mobile,tooltip=excluded.tooltip,
 icon=excluded.icon,resource_group=excluded.resource_group;

COMMIT;
