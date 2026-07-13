INSERT INTO presentation.ui_resource_v1 (
    resource_key, locale_code, caption, caption_short, caption_mobile,
    tooltip, icon, resource_group
)
VALUES
    ('research.gross_attribution.available', 'ru', 'Доступно полностью', 'Доступно', 'Доступно', 'Gross expectancy и gross profit factor сохранены', '', 'research'),
    ('research.gross_attribution.partial_expectancy_available', 'ru', 'Частично: gross expectancy рассчитана, gross PF требует trade-level replay', 'Частично доступно', 'Частично', 'Точная gross expectancy сохранена; gross profit factor требует повтора на уровне сделок', '', 'research'),
    ('research.gross_attribution.unavailable', 'ru', 'Недоступно: gross-атрибуция не рассчитана', 'Недоступно', 'Нет данных', 'Для испытания отсутствует gross/net attribution', '', 'research'),
    ('research.gross_attribution.unavailable_no_gross_metric', 'ru', 'Недоступно: устаревший статус диагностики', 'Устаревший статус', 'Устарело', 'Диагностику необходимо пересчитать с привязкой к gross/net attribution', '', 'research')
ON CONFLICT (resource_key, locale_code) DO UPDATE
SET caption = EXCLUDED.caption,
    caption_short = EXCLUDED.caption_short,
    caption_mobile = EXCLUDED.caption_mobile,
    tooltip = EXCLUDED.tooltip,
    icon = EXCLUDED.icon,
    resource_group = EXCLUDED.resource_group;
