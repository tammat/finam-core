INSERT INTO presentation.ui_resource_v1
(resource_key, locale_code, caption, caption_short, caption_mobile, tooltip, icon, resource_group)
VALUES
('portfolio.column.instrument','ru','Инструмент','Инструмент','Инстр.','Инструмент портфеля','', 'workspace_v2_portfolio'),
('portfolio.column.symbol','ru','Тикер','Тикер','Тикер','Биржевой код инструмента','', 'workspace_v2_portfolio'),
('portfolio.column.name','ru','Название','Название','Назв.','Название инструмента','', 'workspace_v2_portfolio'),
('portfolio.column.quantity','ru','Количество','Кол-во','Кол.','Количество инструмента','', 'workspace_v2_portfolio'),
('portfolio.column.position','ru','Позиция','Позиция','Поз.','Размер позиции','', 'workspace_v2_portfolio'),
('portfolio.column.price','ru','Цена','Цена','Цена','Цена инструмента','', 'workspace_v2_portfolio'),
('portfolio.column.market_value','ru','Рыночная стоимость','Рын. стоимость','Стоимость','Рыночная стоимость позиции','', 'workspace_v2_portfolio'),
('portfolio.column.pnl','ru','Финансовый результат','Результат','Рез.','Финансовый результат позиции','', 'workspace_v2_portfolio'),
('portfolio.column.pnl_pct','ru','Финансовый результат, %','Результат, %','Рез. %','Финансовый результат в процентах','', 'workspace_v2_portfolio'),
('portfolio.column.currency','ru','Валюта','Валюта','Вал.','Валюта показателя','', 'workspace_v2_portfolio'),
('portfolio.column.risk','ru','Риск','Риск','Риск','Риск позиции или портфеля','', 'workspace_v2_portfolio'),
('portfolio.column.updated_at','ru','Обновлено','Обновлено','Обн.','Время последнего обновления','', 'workspace_v2_portfolio')
ON CONFLICT(resource_key, locale_code)
DO UPDATE SET
  caption=EXCLUDED.caption,
  caption_short=EXCLUDED.caption_short,
  caption_mobile=EXCLUDED.caption_mobile,
  tooltip=EXCLUDED.tooltip,
  icon=EXCLUDED.icon,
  resource_group=EXCLUDED.resource_group;
