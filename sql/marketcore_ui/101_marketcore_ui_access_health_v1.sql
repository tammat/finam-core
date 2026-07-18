BEGIN;

CREATE TABLE IF NOT EXISTS marketcore_ui.marketcore_ui_access_health_v1 (
    check_id BIGSERIAL PRIMARY KEY,
    checked_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    internal_status TEXT NOT NULL,
    external_status TEXT NOT NULL,
    overall_status TEXT NOT NULL,
    server_ip TEXT NOT NULL,
    expected_server_ip TEXT NOT NULL,
    external_port INTEGER NOT NULL,
    ui_service_status TEXT NOT NULL,
    internal_home_ok BOOLEAN NOT NULL,
    internal_research_ok BOOLEAN NOT NULL,
    internal_i18n_ok BOOLEAN NOT NULL,
    external_home_ok BOOLEAN NOT NULL,
    external_research_ok BOOLEAN NOT NULL,
    external_i18n_ok BOOLEAN NOT NULL,
    reason_code TEXT NOT NULL,
    recovery_required BOOLEAN NOT NULL DEFAULT false,
    source_version TEXT NOT NULL DEFAULT 'MARKETCORE_UI_ACCESS_HEALTH_V1'
);

CREATE INDEX IF NOT EXISTS marketcore_ui_access_health_checked_idx
ON marketcore_ui.marketcore_ui_access_health_v1 (checked_at DESC);

GRANT USAGE ON SCHEMA marketcore_ui TO alex;
GRANT SELECT, INSERT, DELETE ON marketcore_ui.marketcore_ui_access_health_v1 TO alex;
GRANT USAGE, SELECT ON SEQUENCE marketcore_ui.marketcore_ui_access_health_v1_check_id_seq TO alex;

COMMIT;
