INSERT INTO presentation.ui_resource_v1
(resource_key,locale_code,caption,caption_short,caption_mobile,tooltip,icon,resource_group,is_active,source_version,display_order,priority)
VALUES
('home.card.edge.title','ru','Edge · OOS','Edge · OOS','Edge','Поиск, качество данных и OOS-проверка торговых преимуществ','',
 'home.navigation',true,'HOME_EDGE_NAVIGATION_V1',35,35)
ON CONFLICT(resource_key,locale_code) DO UPDATE SET
caption=excluded.caption,caption_short=excluded.caption_short,caption_mobile=excluded.caption_mobile,
tooltip=excluded.tooltip,resource_group=excluded.resource_group,is_active=true,source_version=excluded.source_version,
display_order=excluded.display_order,priority=excluded.priority,updated_at=now();
