BEGIN;
INSERT INTO presentation.ui_resource_v1
 (resource_key,locale_code,caption,caption_short,caption_mobile,tooltip,icon,resource_group)
VALUES
 ('home.operator.next.view','ru','Посмотреть','Посмотреть','Просмотр','Открыть причины, эффект, статус и срок без выполнения команды.','','workspace_v2_home_operator')
ON CONFLICT(resource_key,locale_code) DO UPDATE SET caption=excluded.caption,
 caption_short=excluded.caption_short,caption_mobile=excluded.caption_mobile,
 tooltip=excluded.tooltip,resource_group=excluded.resource_group;
COMMIT;
