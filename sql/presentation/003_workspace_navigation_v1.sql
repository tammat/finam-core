CREATE SCHEMA IF NOT EXISTS presentation;

CREATE TABLE IF NOT EXISTS presentation.ui_navigation_group_v1 (
    group_code TEXT PRIMARY KEY,
    resource_key TEXT NOT NULL,
    icon TEXT NOT NULL DEFAULT '',
    display_order INTEGER NOT NULL DEFAULT 100,
    workspace_role TEXT NOT NULL DEFAULT 'OPERATOR',
    display_profile TEXT NOT NULL DEFAULT 'DESKTOP',
    required_permission TEXT NOT NULL DEFAULT '',
    is_public BOOLEAN NOT NULL DEFAULT true,
    is_enabled BOOLEAN NOT NULL DEFAULT true,
    source_version TEXT NOT NULL DEFAULT 'WORKSPACE_NAVIGATION_V1',
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS presentation.ui_navigation_item_v1 (
    item_code TEXT PRIMARY KEY,
    group_code TEXT NOT NULL REFERENCES presentation.ui_navigation_group_v1(group_code),
    resource_key TEXT NOT NULL,
    route TEXT NOT NULL,
    icon TEXT NOT NULL DEFAULT '',
    display_order INTEGER NOT NULL DEFAULT 100,
    workspace_role TEXT NOT NULL DEFAULT 'OPERATOR',
    display_profile TEXT NOT NULL DEFAULT 'DESKTOP',
    required_permission TEXT NOT NULL DEFAULT '',
    is_public BOOLEAN NOT NULL DEFAULT true,
    is_enabled BOOLEAN NOT NULL DEFAULT true,
    source_version TEXT NOT NULL DEFAULT 'WORKSPACE_NAVIGATION_V1',
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

INSERT INTO presentation.ui_navigation_group_v1
(group_code, resource_key, icon, display_order)
VALUES
('HOME','navigation.group.home','⌂',1),
('EDGE','navigation.group.edge','🏭',2),
('TRADING','navigation.group.trading','📊',3),
('MARKET','navigation.group.market','🌍',4),
('SYSTEM','navigation.group.system','⚙',5)
ON CONFLICT(group_code) DO UPDATE SET
    resource_key=EXCLUDED.resource_key,
    icon=EXCLUDED.icon,
    display_order=EXCLUDED.display_order,
    is_enabled=true,
    updated_at=now();

INSERT INTO presentation.ui_navigation_item_v1
(item_code, group_code, resource_key, route, icon, display_order)
VALUES
('MISSION_CONTROL','HOME','navigation.item.mission_control','/','⌂',1),
('EDGE_FACTORY','EDGE','navigation.item.edge_factory','/edge-factory','🏭',1),
('DISCOVERY','EDGE','navigation.item.discovery','/edge-discovery','🔁',2),
('RESEARCH','EDGE','navigation.item.research','/research','⌕',3),
('RECOMMENDATION','EDGE','navigation.item.recommendation','/recommendation','🎯',4),
('PAPER_MTM','TRADING','navigation.item.paper_mtm','/paper-mtm','📊',1),
('RUNTIME','TRADING','navigation.item.runtime','/runtime-view','🟢',2),
('PORTFOLIO','TRADING','navigation.item.portfolio','/portfolio','◉',3),
('RISK','TRADING','navigation.item.risk','/risk','⚠',4),
('MARKET_MODEL','MARKET','navigation.item.market_model','/market-model','🧩',1),
('SETTINGS','SYSTEM','navigation.item.settings','/settings','⚙',1),
('LOGS','SYSTEM','navigation.item.logs','/logs','≡',2)
ON CONFLICT(item_code) DO UPDATE SET
    group_code=EXCLUDED.group_code,
    resource_key=EXCLUDED.resource_key,
    route=EXCLUDED.route,
    icon=EXCLUDED.icon,
    display_order=EXCLUDED.display_order,
    is_enabled=true,
    updated_at=now();

INSERT INTO presentation.ui_resource_v1
(resource_key, locale_code, caption, caption_short, caption_mobile, tooltip, icon, resource_group)
VALUES
('navigation.group.home','ru','Главная','Home','Home','Главная рабочая область','⌂','navigation'),
('navigation.group.edge','ru','Edge Factory','Edge','Edge','Поиск и проверка edge','🏭','navigation'),
('navigation.group.trading','ru','Trading','Trading','Trade','Paper, Runtime, Portfolio, Risk','📊','navigation'),
('navigation.group.market','ru','Market','Market','Mkt','Market Model и рыночные параметры','🌍','navigation'),
('navigation.group.system','ru','System','System','Sys','Системные разделы','⚙','navigation'),

('navigation.item.mission_control','ru','Mission Control','Home','Home','Главная панель оператора','⌂','navigation'),
('navigation.item.edge_factory','ru','Edge Factory','Factory','Edge','Фабрика поиска edge','🏭','navigation'),
('navigation.item.discovery','ru','Discovery Loop','Discovery','Loop','Автономный цикл поиска edge','🔁','navigation'),
('navigation.item.research','ru','Research','Research','Res','Исследования','⌕','navigation'),
('navigation.item.recommendation','ru','Recommendation','Reco','Reco','Рекомендации','🎯','navigation'),
('navigation.item.paper_mtm','ru','Paper MTM','Paper','Paper','Paper mark-to-market','📊','navigation'),
('navigation.item.runtime','ru','Runtime','Runtime','Run','Состояние runtime','🟢','navigation'),
('navigation.item.portfolio','ru','Portfolio','Portfolio','Port','Портфель','◉','navigation'),
('navigation.item.risk','ru','Risk','Risk','Risk','Риски','⚠','navigation'),
('navigation.item.market_model','ru','Market Model','Market','Mkt','Модель рынка','🧩','navigation'),
('navigation.item.settings','ru','Settings','Settings','Set','Настройки','⚙','navigation'),
('navigation.item.logs','ru','Logs','Logs','Logs','Журналы','≡','navigation')
ON CONFLICT(resource_key, locale_code) DO UPDATE SET
    caption=EXCLUDED.caption,
    caption_short=EXCLUDED.caption_short,
    caption_mobile=EXCLUDED.caption_mobile,
    tooltip=EXCLUDED.tooltip,
    icon=EXCLUDED.icon,
    resource_group=EXCLUDED.resource_group,
    updated_at=now();

GRANT ALL PRIVILEGES ON presentation.ui_navigation_group_v1 TO alex;
GRANT ALL PRIVILEGES ON presentation.ui_navigation_item_v1 TO alex;
GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA presentation TO alex;

GRANT USAGE ON SCHEMA presentation TO alex;
GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA presentation TO alex;
GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA presentation TO alex;
