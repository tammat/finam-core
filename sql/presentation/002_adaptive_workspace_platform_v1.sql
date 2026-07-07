CREATE SCHEMA IF NOT EXISTS presentation;

ALTER TABLE presentation.ui_resource_v1
ADD COLUMN IF NOT EXISTS caption_short TEXT NOT NULL DEFAULT '',
ADD COLUMN IF NOT EXISTS caption_mobile TEXT NOT NULL DEFAULT '',
ADD COLUMN IF NOT EXISTS display_order INTEGER NOT NULL DEFAULT 100,
ADD COLUMN IF NOT EXISTS priority INTEGER NOT NULL DEFAULT 100;

CREATE TABLE IF NOT EXISTS presentation.ui_widget_v1 (
    widget_code TEXT PRIMARY KEY,
    resource_key TEXT NOT NULL,
    widget_group TEXT NOT NULL,
    min_width INTEGER NOT NULL DEFAULT 320,
    priority INTEGER NOT NULL DEFAULT 100,
    is_active BOOLEAN NOT NULL DEFAULT true,
    source_version TEXT NOT NULL DEFAULT 'ADAPTIVE_WORKSPACE_PLATFORM_V1',
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS presentation.ui_workspace_widget_v1 (
    workspace_code TEXT NOT NULL,
    widget_code TEXT NOT NULL REFERENCES presentation.ui_widget_v1(widget_code),
    display_mode TEXT NOT NULL DEFAULT 'desktop',
    display_order INTEGER NOT NULL DEFAULT 100,
    is_visible BOOLEAN NOT NULL DEFAULT true,
    source_version TEXT NOT NULL DEFAULT 'ADAPTIVE_WORKSPACE_PLATFORM_V1',
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    PRIMARY KEY (workspace_code, widget_code, display_mode)
);

INSERT INTO presentation.ui_widget_v1
(widget_code, resource_key, widget_group, min_width, priority)
VALUES
('EDGE_KPI','edge.factory.title','edge_factory',320,1),
('EDGE_FUNNEL','edge.factory.section.funnel','edge_factory',768,2),
('EDGE_BOTTLENECK','edge.factory.section.bottleneck','edge_factory',320,3),
('EDGE_ACTIONS','edge.factory.section.actions','edge_factory',320,4)
ON CONFLICT(widget_code) DO UPDATE SET
    resource_key=EXCLUDED.resource_key,
    widget_group=EXCLUDED.widget_group,
    min_width=EXCLUDED.min_width,
    priority=EXCLUDED.priority,
    is_active=true,
    updated_at=now();

INSERT INTO presentation.ui_workspace_widget_v1
(workspace_code, widget_code, display_mode, display_order)
VALUES
('EDGE_FACTORY','EDGE_KPI','desktop',1),
('EDGE_FACTORY','EDGE_FUNNEL','desktop',2),
('EDGE_FACTORY','EDGE_BOTTLENECK','desktop',3),
('EDGE_FACTORY','EDGE_ACTIONS','desktop',4),
('EDGE_FACTORY','EDGE_KPI','mobile',1),
('EDGE_FACTORY','EDGE_BOTTLENECK','mobile',2),
('EDGE_FACTORY','EDGE_ACTIONS','mobile',3)
ON CONFLICT(workspace_code, widget_code, display_mode) DO UPDATE SET
    display_order=EXCLUDED.display_order,
    is_visible=true,
    updated_at=now();

GRANT USAGE ON SCHEMA presentation TO alex;
GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA presentation TO alex;
