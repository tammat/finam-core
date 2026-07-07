CREATE SCHEMA IF NOT EXISTS presentation;

UPDATE presentation.ui_navigation_item_v1
SET is_enabled=false, updated_at=now()
WHERE item_code IN (
  'FEATURE_STORE',
  'KNOWLEDGE_GRAPH',
  'TRADING_PLATFORM',
  'PORTFOLIO_PLATFORM',
  'STRATEGY_GOVERNANCE',
  'EDGE_PLATFORM',
  'RUNTIME_VIEW'
);

INSERT INTO presentation.ui_navigation_item_v1
(item_code, group_code, resource_key, route, icon, display_order, workspace_role, display_profile)
VALUES
('MAX_EDGE','EDGE','navigation.item.max_edge','/max-edge','🎯',2,'OPERATOR','DESKTOP'),
('DISCOVERY_CONTROL','EDGE','navigation.item.discovery_control','/edge-discovery','🔁',3,'OPERATOR','DESKTOP')
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
('navigation.item.max_edge','ru','Максимальный edge','Max Edge','Edge','Рейтинг текущих edge','🎯','navigation'),
('navigation.item.discovery_control','ru','Управление Discovery','Discovery','Loop','Управление циклом поиска edge','🔁','navigation'),
('edge.factory.console.title','ru','Edge Factory','Factory','Edge','Операторская консоль Edge Factory','🏭','edge_factory'),
('edge.factory.console.actions','ru','Действия','Actions','Act','Команды через command queue','','edge_factory'),
('edge.factory.console.max_edge','ru','Максимальный edge','Max Edge','Edge','Текущий лидер рейтинга edge','','edge_factory'),
('edge.factory.console.bottleneck','ru','Узкое место','Bottleneck','Block','Текущее узкое место фабрики','','edge_factory'),
('edge.factory.console.queue','ru','Очередь','Queue','Q','Очередь Discovery','','edge_factory')
ON CONFLICT(resource_key, locale_code) DO UPDATE SET
  caption=EXCLUDED.caption,
  caption_short=EXCLUDED.caption_short,
  caption_mobile=EXCLUDED.caption_mobile,
  tooltip=EXCLUDED.tooltip,
  icon=EXCLUDED.icon,
  resource_group=EXCLUDED.resource_group,
  updated_at=now();

GRANT USAGE ON SCHEMA presentation TO finam;
GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA presentation TO finam;
GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA presentation TO finam;
