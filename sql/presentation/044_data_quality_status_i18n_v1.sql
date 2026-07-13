INSERT INTO presentation.ui_resource_v1 (
    resource_key, locale_code, caption, caption_short, caption_mobile,
    tooltip, icon, resource_group
)
VALUES
    ('status.ready', 'ru', 'Готово', 'Готово', 'Готово', 'Источник данных готов', '', 'status'),
    ('status.degraded', 'ru', 'Деградация', 'Деградация', 'Деград.', 'Качество источника снижено', '', 'status'),
    ('status.blocked', 'ru', 'Заблокировано', 'Блок', 'Блок', 'Использование источника заблокировано', '', 'status'),
    ('error.data_quality.insufficient_bars', 'ru', 'Недостаточно баров', 'Мало баров', 'Мало баров', 'Недостаточно исторических баров', '', 'error'),
    ('error.data_quality.insufficient_regime_coverage', 'ru', 'Недостаточное покрытие режимов', 'Мало режимов', 'Мало режимов', 'Недостаточно данных по рыночным режимам', '', 'error'),
    ('error.data_quality.insufficient_trading_days', 'ru', 'Недостаточно торговых дней', 'Мало дней', 'Мало дней', 'Недостаточно торговых сессий', '', 'error'),
    ('error.data_quality.stale_data', 'ru', 'Устаревшие данные', 'Устарело', 'Устарело', 'Последние данные старше допустимого порога', '', 'error')
ON CONFLICT (resource_key, locale_code) DO UPDATE
SET caption = EXCLUDED.caption,
    caption_short = EXCLUDED.caption_short,
    caption_mobile = EXCLUDED.caption_mobile,
    tooltip = EXCLUDED.tooltip,
    icon = EXCLUDED.icon,
    resource_group = EXCLUDED.resource_group;
