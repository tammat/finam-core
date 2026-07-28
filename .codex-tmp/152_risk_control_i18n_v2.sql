INSERT INTO presentation.ui_resource_v1(resource_key,locale_code,caption,caption_short,caption_mobile,tooltip,icon,resource_group)
VALUES
('risk.decision.column.symbol','ru','Инструмент','Инструмент','Инстр.','Инструмент решения риска.','','risk'),
('risk.decision.column.strategy','ru','Стратегия','Стратегия','Страт.','Стратегия решения риска.','','risk'),
('risk.decision.column.decision','ru','Решение','Решение','Решение','Допуск, уменьшение объёма либо блокировка.','','risk'),
('risk.decision.column.reason','ru','Причина','Причина','Причина','Проверки, повлиявшие на решение.','','risk'),
('risk.decision.column.quantity','ru','Объём: допущен/запрошен','Объём','Объём','Сначала объём ограничивается риском до стопа, затем лимитами портфеля.','','risk'),
('risk.decision.column.risk','ru','Риск-бюджет, ₽','Риск, ₽','Риск','Максимальный допустимый убыток до стопа.','','risk'),
('risk.decision.column.spread','ru','Спред, б.п.','Спред','Спред','Последний наблюдаемый спред в базисных пунктах.','','risk'),
('risk.decision.column.book','ru','Глубина стакана','Стакан','Стакан','Минимальная глубина по лучшим bid/ask.','','risk'),
('risk.decision.column.time','ru','Время решения','Время','Время','Время формирования решения.','','risk')
ON CONFLICT (resource_key,locale_code) DO UPDATE SET
 caption=EXCLUDED.caption,caption_short=EXCLUDED.caption_short,caption_mobile=EXCLUDED.caption_mobile,
 tooltip=EXCLUDED.tooltip,icon=EXCLUDED.icon,resource_group=EXCLUDED.resource_group,updated_at=clock_timestamp();
