CREATE TABLE IF NOT EXISTS analytics.edge_discovery_autorun_history_v1 (
    id BIGSERIAL PRIMARY KEY,
    started_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    finished_at TIMESTAMPTZ,
    duration_seconds NUMERIC(12,3) NOT NULL DEFAULT 0,
    scheduler_runs INTEGER NOT NULL DEFAULT 0,
    worker_runs INTEGER NOT NULL DEFAULT 0,
    status TEXT NOT NULL DEFAULT 'STARTED',
    reason TEXT NOT NULL DEFAULT '',
    unsafe_rows INTEGER NOT NULL DEFAULT 0,
    source_version TEXT NOT NULL DEFAULT 'EDGE_DISCOVERY_AUTORUN_TIMER_V1',
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_edge_discovery_autorun_history_ts_v1
ON analytics.edge_discovery_autorun_history_v1(started_at DESC);

INSERT INTO presentation.ui_resource_v1
(resource_key, locale_code, caption, caption_short, caption_mobile, tooltip, icon, resource_group)
VALUES
('edge.discovery.autorun.title','ru','Автозапуск поиска edge','Autorun','Auto','Автоматический запуск Scheduler и Worker','🔁','edge_discovery'),
('edge.discovery.autorun.running','ru','Выполняется','Running','Run','Автозапуск выполняется','','edge_discovery'),
('edge.discovery.autorun.idle','ru','Ожидание','Idle','Idle','Интервал запуска ещё не наступил','','edge_discovery'),
('edge.discovery.autorun.blocked','ru','Заблокировано','Blocked','Block','Автозапуск заблокирован настройками или безопасностью','','edge_discovery'),
('edge.discovery.autorun.finished','ru','Завершено','Finished','Done','Автозапуск завершён','','edge_discovery')
ON CONFLICT(resource_key, locale_code) DO UPDATE SET
caption=EXCLUDED.caption,
caption_short=EXCLUDED.caption_short,
caption_mobile=EXCLUDED.caption_mobile,
tooltip=EXCLUDED.tooltip,
icon=EXCLUDED.icon,
resource_group=EXCLUDED.resource_group,
updated_at=now();

GRANT ALL PRIVILEGES ON analytics.edge_discovery_autorun_history_v1 TO alex;
GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA analytics TO alex;
