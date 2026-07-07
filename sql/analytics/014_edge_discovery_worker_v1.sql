ALTER TABLE analytics.edge_discovery_queue_v1
ADD COLUMN IF NOT EXISTS worker_name TEXT,
ADD COLUMN IF NOT EXISTS worker_pid BIGINT,
ADD COLUMN IF NOT EXISTS execution_seconds NUMERIC(12,3),
ADD COLUMN IF NOT EXISTS error_message TEXT;

INSERT INTO presentation.ui_resource_v1
(resource_key, locale_code, caption, caption_short, caption_mobile, tooltip, icon, resource_group)
VALUES
('edge.discovery.worker.title','ru','Worker поиска edge','Worker','Worker','Исполнитель очереди поиска edge','⚙','edge_discovery'),
('edge.discovery.worker.done','ru','Выполнено','Done','OK','Задача успешно выполнена','','edge_discovery'),
('edge.discovery.worker.error','ru','Ошибка','Error','Err','Ошибка выполнения задачи','','edge_discovery')
ON CONFLICT(resource_key, locale_code) DO UPDATE SET
caption=EXCLUDED.caption,
caption_short=EXCLUDED.caption_short,
caption_mobile=EXCLUDED.caption_mobile,
tooltip=EXCLUDED.tooltip,
icon=EXCLUDED.icon,
resource_group=EXCLUDED.resource_group,
updated_at=now();

GRANT ALL PRIVILEGES ON analytics.edge_discovery_queue_v1 TO alex;
GRANT ALL PRIVILEGES ON analytics.edge_discovery_history_v1 TO alex;
GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA analytics TO alex;
