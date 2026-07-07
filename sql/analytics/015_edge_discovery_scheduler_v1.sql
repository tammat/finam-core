CREATE TABLE IF NOT EXISTS analytics.edge_discovery_scheduler_v1 (
    id BIGSERIAL PRIMARY KEY,
    scheduler_ts TIMESTAMPTZ NOT NULL DEFAULT now(),
    scheduler_code TEXT NOT NULL DEFAULT 'EDGE_DISCOVERY_SCHEDULER',
    profile TEXT NOT NULL DEFAULT 'DEFAULT',
    interval_minutes INTEGER NOT NULL DEFAULT 60,
    queued_count INTEGER NOT NULL DEFAULT 0,
    skipped_count INTEGER NOT NULL DEFAULT 0,
    status TEXT NOT NULL DEFAULT 'ACTIVE',
    reason TEXT NOT NULL DEFAULT '',
    source_version TEXT NOT NULL DEFAULT 'EDGE_DISCOVERY_SCHEDULER_V1',
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_edge_discovery_scheduler_ts_v1
ON analytics.edge_discovery_scheduler_v1(scheduler_ts DESC);

INSERT INTO presentation.ui_resource_v1
(resource_key, locale_code, caption, caption_short, caption_mobile, tooltip, icon, resource_group)
VALUES
('edge.discovery.scheduler.title','ru','Планировщик поиска edge','Scheduler','Sched','Планировщик автоматического цикла поиска edge','⏱','edge_discovery'),
('edge.discovery.scheduler.queued','ru','Поставлено задач','Queued','Q','Количество задач, добавленных в очередь','','edge_discovery'),
('edge.discovery.scheduler.skipped','ru','Пропущено','Skipped','Skip','Количество пропущенных задач','','edge_discovery'),
('edge.discovery.scheduler.status','ru','Статус планировщика','Status','Стат.','Текущий статус планировщика','','edge_discovery')
ON CONFLICT(resource_key, locale_code) DO UPDATE SET
caption=EXCLUDED.caption,
caption_short=EXCLUDED.caption_short,
caption_mobile=EXCLUDED.caption_mobile,
tooltip=EXCLUDED.tooltip,
icon=EXCLUDED.icon,
resource_group=EXCLUDED.resource_group,
updated_at=now();

GRANT ALL PRIVILEGES ON analytics.edge_discovery_scheduler_v1 TO alex;
GRANT ALL PRIVILEGES ON analytics.edge_discovery_queue_v1 TO alex;
GRANT ALL PRIVILEGES ON analytics.edge_discovery_history_v1 TO alex;
GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA analytics TO alex;
