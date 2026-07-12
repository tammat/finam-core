INSERT INTO presentation.ui_resource_v1
(resource_key, locale_code, caption, caption_short, caption_mobile, tooltip, icon, resource_group)
VALUES
('portfolio.statusbar.title','ru','Статус портфеля','Статус','Статус','Текущее состояние данных портфеля','','portfolio_statusbar'),
('portfolio.statusbar.subtitle','ru','Оперативное состояние','Состояние','Статус','Контроль источника и свежести','','portfolio_statusbar'),
('portfolio.statusbar.status','ru','Данные','Данные','Данные','Доступность данных','','portfolio_statusbar'),
('portfolio.statusbar.scope','ru','Контур','Контур','Контур','Контур данных REAL или TEST','','portfolio_statusbar'),
('portfolio.statusbar.timezone','ru','Часовой пояс','TZ','TZ','Часовой пояс отображения дат','','portfolio_statusbar'),
('portfolio.statusbar.currency','ru','Валюта','Валюта','Вал.','Валюта отображения','','portfolio_statusbar'),
('portfolio.statusbar.broker','ru','Брокер','Брокер','Брокер','Выбранный брокерский контур','','portfolio_statusbar'),
('portfolio.statusbar.moex','ru','Индекс MOEX','MOEX','MOEX','Текущее значение индекса Московской биржи','','portfolio_statusbar'),
('portfolio.statusbar.moex_change','ru','К пред. дню','Изм.','Изм.','Изменение к предыдущему торговому дню','','portfolio_statusbar'),
('portfolio.statusbar.moex_freshness','ru','MOEX данные','Свежесть','Свеж.','Свежесть источника индекса','','portfolio_statusbar'),
('portfolio.statusbar.positions','ru','Позиций','Позиций','Поз.','Количество позиций','','portfolio_statusbar'),
('portfolio.statusbar.updated','ru','Обновлено','Обновлено','Время','Время последнего снимка','','portfolio_statusbar')
ON CONFLICT(resource_key, locale_code) DO UPDATE SET
caption=EXCLUDED.caption, caption_short=EXCLUDED.caption_short,
caption_mobile=EXCLUDED.caption_mobile, tooltip=EXCLUDED.tooltip,
icon=EXCLUDED.icon, resource_group=EXCLUDED.resource_group, updated_at=now();
