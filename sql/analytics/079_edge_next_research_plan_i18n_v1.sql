INSERT INTO presentation.ui_resource_v1
(resource_key,locale_code,caption,caption_short,caption_mobile,tooltip,icon,resource_group) VALUES
('research.tile.next_plan','ru','Следующий план','План','План','Количество приоритетных направлений следующего исследования','','research'),
('research.tile.next_variants','ru','Новые варианты','Варианты','Вар.','Количество новых наборов параметров в следующем исследовании','','research')
ON CONFLICT(resource_key,locale_code) DO UPDATE SET
caption=EXCLUDED.caption,caption_short=EXCLUDED.caption_short,caption_mobile=EXCLUDED.caption_mobile,
tooltip=EXCLUDED.tooltip,icon=EXCLUDED.icon,resource_group=EXCLUDED.resource_group;
