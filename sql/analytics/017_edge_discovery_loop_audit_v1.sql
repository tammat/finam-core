CREATE TABLE IF NOT EXISTS analytics.edge_discovery_loop_audit_v1 (
    id BIGSERIAL PRIMARY KEY,
    audit_ts TIMESTAMPTZ NOT NULL DEFAULT now(),
    audit_name TEXT NOT NULL,
    check_name TEXT NOT NULL,
    result TEXT NOT NULL,
    details JSONB NOT NULL DEFAULT '{}'::jsonb,
    source_version TEXT NOT NULL DEFAULT 'EDGE_DISCOVERY_LOOP_AUDIT_V1',
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_edge_discovery_loop_audit_ts_v1
ON analytics.edge_discovery_loop_audit_v1(audit_ts DESC);

INSERT INTO presentation.ui_resource_v1
(resource_key, locale_code, caption, caption_short, caption_mobile, tooltip, icon, resource_group)
VALUES
('edge.discovery.audit.title','ru','Аудит цикла поиска edge','Audit','Audit','Проверка полного контура Scheduler → Queue → Worker → Research → History','🔎','edge_discovery'),
('edge.discovery.audit.pass','ru','Пройдено','PASS','OK','Проверка успешно пройдена','','edge_discovery'),
('edge.discovery.audit.fail','ru','Ошибка','FAIL','Fail','Проверка не пройдена','','edge_discovery'),
('edge.discovery.audit.warning','ru','Предупреждение','WARN','Warn','Проверка требует внимания','','edge_discovery'),
('edge.discovery.audit.overall','ru','Итог аудита','Overall','Итог','Общий результат аудита Discovery Loop','','edge_discovery')
ON CONFLICT(resource_key, locale_code) DO UPDATE SET
caption=EXCLUDED.caption,
caption_short=EXCLUDED.caption_short,
caption_mobile=EXCLUDED.caption_mobile,
tooltip=EXCLUDED.tooltip,
icon=EXCLUDED.icon,
resource_group=EXCLUDED.resource_group,
updated_at=now();

GRANT ALL PRIVILEGES ON analytics.edge_discovery_loop_audit_v1 TO alex;
GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA analytics TO alex;
