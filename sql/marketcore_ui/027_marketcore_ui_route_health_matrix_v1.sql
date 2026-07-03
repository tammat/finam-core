BEGIN;

CREATE TABLE IF NOT EXISTS marketcore_ui.marketcore_ui_route_health_matrix_v1 (
    route TEXT PRIMARY KEY,
    label_ru TEXT NOT NULL DEFAULT '',
    group_key TEXT NOT NULL DEFAULT '',
    group_title_ru TEXT NOT NULL DEFAULT '',
    menu_order INTEGER NOT NULL DEFAULT 0,
    http_status INTEGER NOT NULL DEFAULT 0,
    http_ok BOOLEAN NOT NULL DEFAULT false,
    contains_shell_marker BOOLEAN NOT NULL DEFAULT false,
    content_length INTEGER NOT NULL DEFAULT 0,
    issue TEXT NOT NULL DEFAULT '',
    checked_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    source_version TEXT NOT NULL DEFAULT 'MARKETCORE_UI_8080_ROUTE_HEALTH_MATRIX_V1',
    build_id TEXT NOT NULL DEFAULT 'manual'
);

GRANT USAGE ON SCHEMA marketcore_ui TO alex;
GRANT SELECT, INSERT, UPDATE, DELETE ON marketcore_ui.marketcore_ui_route_health_matrix_v1 TO alex;

COMMIT;

SELECT 'MARKETCORE_UI_ROUTE_HEALTH_MATRIX_SCHEMA_V1_READY' AS verdict;
