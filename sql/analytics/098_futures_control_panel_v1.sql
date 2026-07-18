BEGIN;
INSERT INTO presentation.ui_resource_v1
(resource_key,locale_code,caption,caption_short,caption_mobile,tooltip,icon,resource_group) VALUES
('research.futures.title','ru','Фьючерсы','Фьючерсы','Фьюч.','Плечо и автоматическое роллирование BR и NG','','research'),
('research.futures.column.status','ru','Статус','Статус','Ст.','Состояние и прогресс перехода ликвидности','','research'),
('research.futures.column.root','ru','Рынок','Рынок','Рын.','Корень фьючерсного контракта','','research'),
('research.futures.column.current','ru','Текущий','Текущий','Тек.','Ближний ликвидный контракт','','research'),
('research.futures.column.next','ru','Следующий','Следующий','След.','Следующий доступный контракт','','research'),
('research.futures.column.selected','ru','Рабочий','Рабочий','Раб.','Контракт, выбранный системой','','research'),
('research.futures.column.expiry','ru','Дней','Дней','Дн.','Дней до экспирации текущего контракта','','research'),
('research.futures.column.liquidity','ru','Ликвидность','Ликвидн.','Ликв.','Медианные объёмы текущего и следующего контрактов','','research'),
('research.futures.column.decision','ru','Решение','Решение','Реш.','Причина системного выбора контракта','','research'),
('research.futures.column.leverage','ru','Плечо','Плечо','Плечо','Максимальное исследовательское плечо','','research'),
('research.futures.column.limit','ru','Лимит','Лимит','Лим.','Максимальная доля одного инструмента','','research'),
('research.futures.status.ready','ru','Готово','Готово','Гот.','Текущий контракт ликвиден; переход пока не требуется','','research'),
('research.futures.status.watch','ru','Контроль','Контроль','Контр.','Приближается окно роллирования; система контролирует ликвидность','','research'),
('research.futures.status.rolled','ru','Переход','Переход','Ролл','Система выбрала следующий контракт','','research'),
('research.futures.decision.keep_liquid_front','ru','Оставить','Оставить','Ост.','Текущий контракт существенно ликвиднее следующего','','research'),
('research.futures.decision.expiry_window_roll','ru','Перейти','Перейти','Ролл','Наступило разрешённое окно перехода перед экспирацией','','research'),
('research.futures.decision.liquidity_crossover_roll','ru','Перейти','Перейти','Ролл','Ликвидность перешла в следующий контракт','','research'),
('research.futures.liquidity','ru','{current} / {next}','{current}/{next}','{progress_pct}%','Текущий объём: {current}; следующий: {next}; готовность перехода: {progress_pct}%','','research'),
('research.futures.leverage_value','ru','{value}×','{value}×','{value}×','Максимальное плечо {value}×; источник ограничения: {margin_source}','','research'),
('research.futures.percent','ru','{value}%','{value}%','{value}%','Лимит позиции: {value}% капитала с учётом плеча','','research')
ON CONFLICT(resource_key,locale_code) DO UPDATE SET caption=EXCLUDED.caption,
 caption_short=EXCLUDED.caption_short,caption_mobile=EXCLUDED.caption_mobile,
 tooltip=EXCLUDED.tooltip,icon=EXCLUDED.icon,resource_group=EXCLUDED.resource_group;
COMMIT;
