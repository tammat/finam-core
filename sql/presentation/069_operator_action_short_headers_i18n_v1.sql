INSERT INTO presentation.ui_resource_v1 (
    resource_key, locale_code, caption, caption_short, caption_mobile,
    tooltip, icon, resource_group
) VALUES
('column.operator.number','ru','№','№','№','','','column'),
('column.operator.action','ru','Действие','Действие','Действие','','','column'),
('column.operator.reason','ru','Причина','Причина','Причина','','','column'),
('column.operator.effect','ru','Эффект','Эффект','Эффект','','','column'),
('column.operator.confidence','ru','Уверенность','Уверенность','Уверенность','','','column'),
('column.operator.verdict','ru','Вердикт','Вердикт','Вердикт','','','column'),
('column.operator.deadline','ru','Срок','Срок','Срок','','','column')
ON CONFLICT (resource_key, locale_code) DO UPDATE SET
caption=EXCLUDED.caption,caption_short=EXCLUDED.caption_short,
caption_mobile=EXCLUDED.caption_mobile,tooltip=EXCLUDED.tooltip,
icon=EXCLUDED.icon,resource_group=EXCLUDED.resource_group;
