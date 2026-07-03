BEGIN;

CREATE TABLE IF NOT EXISTS marketcore_ui.marketcore_ui_systemd_8080_health_v1 (
    id SMALLINT PRIMARY KEY,

    kg_api_unit TEXT NOT NULL DEFAULT 'marketcore-kg-api.service',
    ui_shell_unit TEXT NOT NULL DEFAULT 'marketcore-ui-shell.service',

    kg_api_active_state TEXT NOT NULL DEFAULT 'unknown',
    kg_api_sub_state TEXT NOT NULL DEFAULT 'unknown',
    kg_api_result TEXT NOT NULL DEFAULT 'unknown',
    kg_api_main_status TEXT NOT NULL DEFAULT '',
    kg_api_healthy BOOLEAN NOT NULL DEFAULT false,

    ui_shell_active_state TEXT NOT NULL DEFAULT 'unknown',
    ui_shell_sub_state TEXT NOT NULL DEFAULT 'unknown',
    ui_shell_result TEXT NOT NULL DEFAULT 'unknown',
    ui_shell_main_status TEXT NOT NULL DEFAULT '',
    ui_shell_healthy BOOLEAN NOT NULL DEFAULT false,

    kg_api_port INTEGER NOT NULL DEFAULT 8095,
    ui_shell_port INTEGER NOT NULL DEFAULT 8080,

    kg_api_http_ok BOOLEAN NOT NULL DEFAULT false,
    ui_home_http_ok BOOLEAN NOT NULL DEFAULT false,
    ui_risk_http_ok BOOLEAN NOT NULL DEFAULT false,
    ui_settings_http_ok BOOLEAN NOT NULL DEFAULT false,

    kg_api_health_status TEXT NOT NULL DEFAULT 'UNKNOWN',
    ui_shell_health_status TEXT NOT NULL DEFAULT 'UNKNOWN',
    overall_status TEXT NOT NULL DEFAULT 'UNKNOWN',

    open_url TEXT NOT NULL DEFAULT '',
    risk_url TEXT NOT NULL DEFAULT '',
    settings_url TEXT NOT NULL DEFAULT '',

    health_reason TEXT NOT NULL DEFAULT '',
    recommended_action TEXT NOT NULL DEFAULT '',

    runtime_changed INTEGER NOT NULL DEFAULT 0,
    execution_changed INTEGER NOT NULL DEFAULT 0,
    orders_changed INTEGER NOT NULL DEFAULT 0,
    fills_changed INTEGER NOT NULL DEFAULT 0,
    micro_live_allowed INTEGER NOT NULL DEFAULT 0,

    refreshed_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    source_version TEXT NOT NULL DEFAULT 'MARKETCORE_UI_SYSTEMD_8080_HEALTH_V1',
    build_id TEXT NOT NULL DEFAULT 'manual'
);

GRANT USAGE ON SCHEMA marketcore_ui TO alex;
GRANT SELECT, INSERT, UPDATE, DELETE ON marketcore_ui.marketcore_ui_systemd_8080_health_v1 TO alex;

COMMIT;

SELECT 'MARKETCORE_UI_SYSTEMD_8080_HEALTH_SCHEMA_V1_READY' AS verdict;
