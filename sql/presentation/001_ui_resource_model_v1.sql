CREATE SCHEMA IF NOT EXISTS presentation;

CREATE TABLE IF NOT EXISTS presentation.ui_resource_v1 (
    resource_key TEXT NOT NULL,
    locale_code TEXT NOT NULL DEFAULT 'ru',
    caption TEXT NOT NULL,
    tooltip TEXT NOT NULL DEFAULT '',
    icon TEXT NOT NULL DEFAULT '',
    hotkey TEXT NOT NULL DEFAULT '',
    resource_group TEXT NOT NULL DEFAULT 'common',
    is_active BOOLEAN NOT NULL DEFAULT true,
    source_version TEXT NOT NULL DEFAULT 'UI_RESOURCE_MODEL_V1',
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    PRIMARY KEY (resource_key, locale_code)
);

INSERT INTO presentation.ui_resource_v1
(resource_key, locale_code, caption, tooltip, icon, hotkey, resource_group)
VALUES
('edge.factory.title','ru','Edge Factory','Главный экран исследовательской фабрики','🏭','','edge_factory'),
('edge.factory.subtitle','ru','Исследовательская фабрика','KPI, bottleneck, рекомендации и действия','','','edge_factory'),
('edge.factory.kpi.research_queue','ru','Research Queue','Очередь исследований','','','edge_factory'),
('edge.factory.kpi.observations','ru','Observations','Наблюдения','','','edge_factory'),
('edge.factory.kpi.candidates','ru','Candidates','Кандидаты edge','','','edge_factory'),
('edge.factory.kpi.validated','ru','Validated','Прошедшие validation','','','edge_factory'),
('edge.factory.kpi.paper','ru','Paper','Активные paper-кандидаты','','','edge_factory'),
('edge.factory.section.funnel','ru','Pipeline Funnel','Воронка исследований','','','edge_factory'),
('edge.factory.section.bottleneck','ru','Current Bottleneck','Текущее узкое место','','','edge_factory'),
('edge.factory.section.actions','ru','Actions','Безопасные управляющие действия','','','edge_factory'),
('edge.factory.action.run_audit','ru','Run audit','Создать заявку на аудит Edge Pipeline','🔎','','edge_factory'),
('edge.factory.action.refresh_market_data','ru','Refresh market data','Создать заявку на обновление рыночных данных','↻','','edge_factory'),
('edge.factory.action.run_recommendation','ru','Run recommendation','Создать заявку на пересчёт рекомендаций','🎯','','edge_factory'),
('edge.factory.action.create_sprint_plan','ru','Create sprint plan','Создать план следующего EDGE Sprint','🧭','','edge_factory'),
('edge.factory.action.paper_reprice','ru','Paper reprice','Создать заявку на перерасчёт Paper MTM','📊','','edge_factory')
ON CONFLICT (resource_key, locale_code) DO UPDATE SET
    caption=EXCLUDED.caption,
    tooltip=EXCLUDED.tooltip,
    icon=EXCLUDED.icon,
    hotkey=EXCLUDED.hotkey,
    resource_group=EXCLUDED.resource_group,
    is_active=true,
    updated_at=now();

GRANT USAGE ON SCHEMA presentation TO alex;
GRANT SELECT, INSERT, UPDATE, DELETE ON presentation.ui_resource_v1 TO alex;
