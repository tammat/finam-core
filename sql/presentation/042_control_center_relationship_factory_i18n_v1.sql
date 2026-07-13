INSERT INTO presentation.ui_resource_v1 (
    resource_key, locale_code, caption, caption_short, caption_mobile,
    tooltip, icon, resource_group
)
VALUES
    ('research.relationship_factory.title', 'ru', 'Фабрика связей', 'Связи', 'Связи', 'Результаты исследования связей', '', 'research'),
    ('research.relationship_factory.summary', 'ru', '{relationships} связей · {trials} проверок · PASS {passed}', '{relationships} · {trials} · {passed}', '{relationships} · {passed}', 'Количество связей, проверок и успешных OOS-проверок', '', 'research'),
    ('column.relationship_family', 'ru', 'Семейство', 'Семейство', 'Семейство', 'Семейство исследуемой связи', '', 'column'),
    ('column.relationship', 'ru', 'Связь', 'Связь', 'Связь', 'Источник и целевой инструмент', '', 'column'),
    ('column.oos_profit_factor', 'ru', 'OOS PF', 'OOS PF', 'PF', 'Profit factor на отложенной выборке', '', 'column'),
    ('column.expectancy_bps', 'ru', 'Ожидание, б.п.', 'Ожидание', 'Ожид.', 'Ожидаемый результат в базисных пунктах', '', 'column'),
    ('column.oos_research_trades', 'ru', 'OOS-сделки (исследование)', 'OOS-сделки', 'Сделки', 'Исторические исследовательские сделки, не брокерские заявки', '', 'column'),
    ('column.coverage', 'ru', 'Покрытие', 'Покрытие', 'Покр.', 'Покрытие наблюдений', '', 'column'),
    ('column.market_regime', 'ru', 'Режим', 'Режим', 'Режим', 'Рыночный режим', '', 'column'),
    ('column.market_session', 'ru', 'Сессия', 'Сессия', 'Сессия', 'Рыночная сессия', '', 'column'),
    ('column.verdict', 'ru', 'Вердикт', 'Вердикт', 'Итог', 'Вердикт OOS-проверки', '', 'column'),
    ('market.regime.all', 'ru', 'Все режимы', 'Все', 'Все', 'Без ограничения рыночного режима', '', 'market'),
    ('market.regime.trend', 'ru', 'Тренд', 'Тренд', 'Тренд', 'Трендовый рыночный режим', '', 'market'),
    ('market.regime.range', 'ru', 'Боковик', 'Боковик', 'Боковик', 'Боковой рыночный режим', '', 'market'),
    ('market.regime.range_normal', 'ru', 'Боковик', 'Боковик', 'Боковик', 'Боковой рыночный режим', '', 'market'),
    ('market.regime.compression', 'ru', 'Сжатие', 'Сжатие', 'Сжатие', 'Режим сжатия волатильности', '', 'market'),
    ('market.regime.expansion', 'ru', 'Расширение', 'Расширение', 'Расшир.', 'Режим расширения волатильности', '', 'market'),
    ('market.regime.trend_up', 'ru', 'Тренд вверх', 'Вверх', 'Вверх', 'Восходящий тренд', '', 'market'),
    ('market.regime.trend_down', 'ru', 'Тренд вниз', 'Вниз', 'Вниз', 'Нисходящий тренд', '', 'market'),
    ('market.regime.trend_up_expansion', 'ru', 'Расширение вверх', 'Рост + расширение', 'Рост', 'Восходящий тренд с расширением волатильности', '', 'market'),
    ('market.regime.trend_down_expansion', 'ru', 'Расширение вниз', 'Снижение + расширение', 'Снижение', 'Нисходящий тренд с расширением волатильности', '', 'market'),
    ('market.session.all', 'ru', 'Все сессии', 'Все', 'Все', 'Без ограничения торговой сессии', '', 'market'),
    ('market.session.moex_first_hour', 'ru', 'Первый час MOEX', 'Первый час', 'Старт MOEX', 'Первый час основной сессии MOEX', '', 'market'),
    ('market.session.moex_close', 'ru', 'Закрытие MOEX', 'Закрытие', 'Закрытие', 'Заключительная часть сессии MOEX', '', 'market'),
    ('market.session.us_open', 'ru', 'Открытие США', 'США', 'США', 'Период открытия американской сессии', '', 'market'),
    ('market.session.europe', 'ru', 'Европейская сессия', 'Европа', 'Европа', 'Европейская торговая сессия', '', 'market'),
    ('status.fail', 'ru', 'Не пройдено', 'FAIL', 'FAIL', 'Проверка не пройдена', '', 'status')
ON CONFLICT (resource_key, locale_code) DO UPDATE
SET caption = EXCLUDED.caption,
    caption_short = EXCLUDED.caption_short,
    caption_mobile = EXCLUDED.caption_mobile,
    tooltip = EXCLUDED.tooltip,
    icon = EXCLUDED.icon,
    resource_group = EXCLUDED.resource_group;
