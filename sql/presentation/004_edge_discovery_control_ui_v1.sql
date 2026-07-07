CREATE SCHEMA IF NOT EXISTS presentation;

CREATE TABLE IF NOT EXISTS presentation.command_queue_v1 (
    id BIGSERIAL PRIMARY KEY,
    command_code TEXT NOT NULL,
    command_status TEXT NOT NULL DEFAULT 'NEW',
    payload JSONB NOT NULL DEFAULT '{}'::jsonb,
    requested_by TEXT NOT NULL DEFAULT current_user,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    started_at TIMESTAMPTZ,
    finished_at TIMESTAMPTZ,
    error_message TEXT,
    source_version TEXT NOT NULL DEFAULT 'EDGE_DISCOVERY_CONTROL_UI_V1'
);

CREATE INDEX IF NOT EXISTS idx_command_queue_v1_status
ON presentation.command_queue_v1(command_status, created_at DESC);

INSERT INTO presentation.ui_resource_v1
(resource_key, locale_code, caption, caption_short, caption_mobile, tooltip, icon, resource_group)
VALUES
('edge.discovery.control.title','ru','Управление поиском edge','Discovery','Loop','Операторская консоль Discovery Loop','🔁','edge_discovery'),
('edge.discovery.control.status','ru','Статус','Status','Стат.','Текущий статус Discovery Loop','','edge_discovery'),
('edge.discovery.control.queue','ru','Очередь','Queue','Q','Очередь задач поиска edge','','edge_discovery'),
('edge.discovery.control.worker','ru','Worker','Worker','W','Исполнитель задач поиска edge','','edge_discovery'),
('edge.discovery.control.scheduler','ru','Планировщик','Scheduler','Sch','Планировщик Discovery Loop','','edge_discovery'),
('edge.discovery.control.audit','ru','Аудит','Audit','Audit','Аудит полного контура Discovery Loop','','edge_discovery'),
('edge.discovery.control.bottleneck','ru','Узкое место','Bottleneck','Block','Текущее узкое место поиска edge','','edge_discovery'),
('edge.discovery.control.events','ru','События','Events','Evt','Последние события Discovery Loop','','edge_discovery'),
('edge.discovery.control.actions','ru','Действия','Actions','Act','Безопасные действия через command queue','','edge_discovery')
ON CONFLICT(resource_key, locale_code) DO UPDATE SET
caption=EXCLUDED.caption,
caption_short=EXCLUDED.caption_short,
caption_mobile=EXCLUDED.caption_mobile,
tooltip=EXCLUDED.tooltip,
icon=EXCLUDED.icon,
resource_group=EXCLUDED.resource_group,
updated_at=now();

GRANT USAGE ON SCHEMA presentation TO alex;
GRANT ALL PRIVILEGES ON presentation.command_queue_v1 TO alex;
GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA presentation TO alex;
