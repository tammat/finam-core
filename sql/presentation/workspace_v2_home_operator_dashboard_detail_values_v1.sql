INSERT INTO presentation.ui_resource_v1
(
    resource_key,
    locale_code,
    caption,
    caption_short,
    caption_mobile,
    tooltip,
    icon,
    resource_group
)
VALUES
('home.operator.rows','ru','Записей','Записей','Зап.','Количество найденных записей','', 'workspace_v2_home_operator'),
('home.operator.status','ru','Статус','Статус','Стат.','Текущее состояние контура','', 'workspace_v2_home_operator'),
('home.operator.updated','ru','Обновлено','Обновлено','Обн.','Последнее обновление','', 'workspace_v2_home_operator')
ON CONFLICT(resource_key,locale_code)
DO UPDATE SET
caption=EXCLUDED.caption,
caption_short=EXCLUDED.caption_short,
caption_mobile=EXCLUDED.caption_mobile,
tooltip=EXCLUDED.tooltip,
icon=EXCLUDED.icon,
resource_group=EXCLUDED.resource_group;
