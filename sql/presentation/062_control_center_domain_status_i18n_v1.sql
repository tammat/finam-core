INSERT INTO presentation.ui_resource_v1 (
    resource_key, locale_code, caption, caption_short, caption_mobile,
    tooltip, icon, resource_group
) VALUES
('status.no_data','ru','Нет данных','Нет данных','Нет данных','','','status'),
('status.current','ru','Актуально','Актуально','Актуально','','','status'),
('status.stale','ru','Устарело','Устарело','Устарело','','','status'),
('status.unavailable','ru','Недоступно','Недоступно','Недоступно','','','status'),
('status.bar_only','ru','Только свечи','Только свечи','Свечи','','','status'),
('status.paper','ru','Бумажная торговля','Paper','Paper','','','status'),
('status.shadow','ru','Теневое наблюдение','Shadow','Shadow','','','status'),
('status.reject','ru','Отклонено','Отклонено','Отклонено','','','status'),
('status.rejected','ru','Отклонено','Отклонено','Отклонено','','','status')
ON CONFLICT (resource_key, locale_code) DO UPDATE SET
caption=EXCLUDED.caption,
caption_short=EXCLUDED.caption_short,
caption_mobile=EXCLUDED.caption_mobile,
tooltip=EXCLUDED.tooltip,
icon=EXCLUDED.icon,
resource_group=EXCLUDED.resource_group;
