INSERT INTO presentation.ui_resource_v1 (
    resource_key,locale_code,caption,caption_short,caption_mobile,
    tooltip,icon,resource_group
)
VALUES
    ('research.recommendation.progress','ru','Открывается раздел рекомендации: {reason}','Открывается: {reason}','Открывается','Подготовка перехода к соответствующему разделу','','research'),
    ('research.recommendation.progress_complete','ru','Раздел рекомендации готов','Готово','Готово','Переход внутри Control Center завершён','','research')
ON CONFLICT (resource_key,locale_code) DO UPDATE
SET caption=EXCLUDED.caption,caption_short=EXCLUDED.caption_short,
    caption_mobile=EXCLUDED.caption_mobile,tooltip=EXCLUDED.tooltip,
    icon=EXCLUDED.icon,resource_group=EXCLUDED.resource_group;
