from pathlib import Path


def test_access_monitor_checks_internal_external_api_and_i18n() -> None:
    source = Path("src/scripts/monitor_marketcore_ui_access_v1.py").read_text()
    assert "http://127.0.0.1:8080" in source
    assert "http://onezh.ddns.net:18080" in source
    assert "/api/v2/domain-render-tree/research" in source
    assert "/api/v2/i18n/catalog?locale=ru-RU" in source
    assert 'return 2 if recovery_required else 0' in source


def test_access_monitor_is_db_audited_and_recovers_only_internal_failure() -> None:
    sql = Path("sql/marketcore_ui/101_marketcore_ui_access_health_v1.sql").read_text()
    service = Path("deploy/systemd/marketcore-ui-access-health.service").read_text()
    recovery = Path("deploy/systemd/marketcore-ui-access-recover.service").read_text()
    timer = Path("deploy/systemd/marketcore-ui-access-health.timer").read_text()
    assert "marketcore_ui_access_health_v1" in sql
    assert "OnFailure=marketcore-ui-access-recover.service" in service
    assert "restart marketcore-ui-shell.service" in recovery
    assert "OnUnitActiveSec=2min" in timer
