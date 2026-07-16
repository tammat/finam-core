INSERT INTO presentation.ui_resource_v1 (
    resource_key, locale_code, caption, caption_short, caption_mobile,
    tooltip, icon, resource_group
) VALUES
(
    'status.observation_id_link_gap', 'ru',
    'Не найдена сквозная связь по идентификатору наблюдения',
    'Нет связи наблюдения', 'Нет связи',
    'Объекты соседних стадий нельзя однозначно сопоставить по observation_id',
    '', 'status'
)
ON CONFLICT (resource_key, locale_code) DO UPDATE SET
caption=EXCLUDED.caption,
caption_short=EXCLUDED.caption_short,
caption_mobile=EXCLUDED.caption_mobile,
tooltip=EXCLUDED.tooltip,
icon=EXCLUDED.icon,
resource_group=EXCLUDED.resource_group;
