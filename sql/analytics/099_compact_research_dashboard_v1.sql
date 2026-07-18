BEGIN;
INSERT INTO presentation.ui_resource_v1
(resource_key,locale_code,caption,caption_short,caption_mobile,tooltip,icon,resource_group) VALUES
('research.futures.card.working','ru','Рабочий','Рабочий','Раб.','Контракт, используемый системой сейчас','','research'),
('research.futures.card.next','ru','Следующий','Следующий','След.','Следующий контракт для возможного перехода','','research'),
('research.futures.card.expiry','ru','До экспирации','Экспирация','Дней','Дней до экспирации текущего контракта','','research'),
('research.futures.card.liquidity','ru','Ликвидность','Ликвидность','Ликв.','Текущий и следующий медианные объёмы','','research'),
('research.futures.card.decision','ru','Решение','Решение','Реш.','Автоматическое решение о роллировании','','research'),
('research.futures.card.leverage','ru','Плечо','Плечо','Плечо','Максимальное разрешённое плечо','','research'),
('research.futures.card.limit','ru','Лимит позиции','Лимит','Лим.','Максимальная доля одного инструмента','','research')
ON CONFLICT(resource_key,locale_code) DO UPDATE SET caption=EXCLUDED.caption,
 caption_short=EXCLUDED.caption_short,caption_mobile=EXCLUDED.caption_mobile,
 tooltip=EXCLUDED.tooltip,icon=EXCLUDED.icon,resource_group=EXCLUDED.resource_group;
COMMIT;
