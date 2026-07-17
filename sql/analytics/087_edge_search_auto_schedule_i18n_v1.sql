INSERT INTO presentation.ui_resource_v1
(resource_key,locale_code,caption,caption_short,caption_mobile,tooltip,icon,resource_group) VALUES
('research.tile.auto_queue','ru','Автопоиск в очереди','Автопоиск','Авто',
 'Количество системных циклов поиска, ожидающих или выполняющих обработку','','research')
ON CONFLICT(resource_key,locale_code) DO UPDATE SET
caption=EXCLUDED.caption,caption_short=EXCLUDED.caption_short,caption_mobile=EXCLUDED.caption_mobile,
tooltip=EXCLUDED.tooltip,icon=EXCLUDED.icon,resource_group=EXCLUDED.resource_group;
