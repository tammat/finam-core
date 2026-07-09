INSERT INTO presentation.ui_resource_v1
(resource_key,locale_code,caption,caption_short,caption_mobile,tooltip,icon,resource_group)
VALUES
('home.card.status.rows','ru','Записей','Записей','Зап.','Количество найденных записей','', 'workspace_v2_home'),
('home.card.status.updated','ru','Последнее обновление','Обновлено','Обн.','Время последнего обновления','', 'workspace_v2_home')
ON CONFLICT(resource_key,locale_code)
DO UPDATE SET
caption=EXCLUDED.caption,
caption_short=EXCLUDED.caption_short,
caption_mobile=EXCLUDED.caption_mobile,
tooltip=EXCLUDED.tooltip,
icon=EXCLUDED.icon,
resource_group=EXCLUDED.resource_group;
