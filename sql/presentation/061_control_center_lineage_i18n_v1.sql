INSERT INTO presentation.ui_resource_v1 (
    resource_key, locale_code, caption, caption_short, caption_mobile,
    tooltip, icon, resource_group
) VALUES
('column.source.identity','ru','Источник данных','Источник','Источник','','','column'),
('column.source.as.of','ru','Данные актуальны на','Актуально на','Актуально','','','column'),
('column.freshness.code','ru','Актуальность данных','Актуальность','Актуальность','','','column'),
('column.quality.code','ru','Качество данных','Качество','Качество','','','column'),
('column.cost.impact','ru','Влияние издержек','Издержки','Издержки','','','column')
ON CONFLICT (resource_key, locale_code) DO UPDATE SET
caption=EXCLUDED.caption,
caption_short=EXCLUDED.caption_short,
caption_mobile=EXCLUDED.caption_mobile,
tooltip=EXCLUDED.tooltip,
icon=EXCLUDED.icon,
resource_group=EXCLUDED.resource_group;
