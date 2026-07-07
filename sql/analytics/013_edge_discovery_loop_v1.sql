CREATE TABLE IF NOT EXISTS analytics.edge_discovery_queue_v1 (
    id BIGSERIAL PRIMARY KEY,
    event_code TEXT NOT NULL,
    priority TEXT NOT NULL DEFAULT 'NORMAL',
    status TEXT NOT NULL DEFAULT 'NEW',
    expected_edge_gain NUMERIC(12,6) NOT NULL DEFAULT 0,
    payload JSONB NOT NULL DEFAULT '{}'::jsonb,
    planned_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    started_at TIMESTAMPTZ,
    finished_at TIMESTAMPTZ,
    source_version TEXT NOT NULL DEFAULT 'EDGE_DISCOVERY_LOOP_V1',
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_edge_discovery_queue_status_v1
ON analytics.edge_discovery_queue_v1(status, priority, planned_at);

CREATE TABLE IF NOT EXISTS analytics.edge_discovery_history_v1 (
    id BIGSERIAL PRIMARY KEY,
    queue_id BIGINT REFERENCES analytics.edge_discovery_queue_v1(id),
    event_code TEXT NOT NULL,
    result_status TEXT NOT NULL,
    result_json JSONB NOT NULL DEFAULT '{}'::jsonb,
    source_version TEXT NOT NULL DEFAULT 'EDGE_DISCOVERY_LOOP_V1',
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

INSERT INTO presentation.ui_resource_v1
(resource_key, locale_code, caption, caption_short, caption_mobile, tooltip, icon, resource_group)
VALUES
('edge.discovery.loop.title','ru','Цикл поиска edge','Discovery Loop','Loop','Автоматический цикл постановки задач на поиск edge','🔁','edge_discovery'),
('edge.discovery.loop.queue','ru','Очередь задач','Очередь','Оч.','Очередь событий discovery loop','','edge_discovery'),
('edge.discovery.loop.history','ru','История цикла','История','Ист.','История выполненных событий discovery loop','','edge_discovery'),
('edge.discovery.loop.event.run_research','ru','Запустить исследование','Research','Res','Поставить задачу параметрического исследования','','edge_discovery'),
('edge.discovery.loop.event.paper_reprice','ru','Пересчитать Paper','Paper','Paper','Поставить задачу перерасчёта Paper MTM','','edge_discovery'),
('edge.discovery.loop.event.recommendation','ru','Пересчитать рекомендации','Reco','Reco','Поставить задачу пересчёта рекомендаций','','edge_discovery')
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
