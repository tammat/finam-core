BEGIN;
INSERT INTO presentation.ui_resource_v1
(resource_key,locale_code,caption,caption_short,caption_mobile,tooltip,icon,resource_group) VALUES
('status.edge_search_started','ru','Поиск запущен','Поиск запущен','Запущен','Системный поиск торгового преимущества выполняется','','status'),
('status.awaiting_forward_readiness','ru','Ожидает готовности Forward','Ожидает Forward','Ожидает','Переход будет разрешён после готовности чистой Forward-когорты','','status')
ON CONFLICT(resource_key,locale_code) DO UPDATE SET caption=EXCLUDED.caption,
 caption_short=EXCLUDED.caption_short,caption_mobile=EXCLUDED.caption_mobile,
 tooltip=EXCLUDED.tooltip,resource_group=EXCLUDED.resource_group;
COMMIT;
