from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_unknown_i18n_status_does_not_abort_atomic_render() -> None:
    source = (ROOT / "src/marketcore/presentation/ui_runtime/assets/v2/browser_presentation_services_v2.js").read_text()
    assert "readableFallback" in source
    assert 'return readableFallback(messageKey)' in source
    assert '"PRESENTATION_V2_MESSAGE_MISSING"' in source


def test_domain_values_never_render_as_javascript_object_or_raw_boolean() -> None:
    source = (ROOT / "src/marketcore/presentation/ui_runtime/assets/v2/browser_presentation_services_v2.js").read_text()
    assert 'case "BOOLEAN": return domainValue(Boolean(value), locale)' in source
    assert 'case "DOMAIN_VALUE": return domainValue(value, locale)' in source
    assert "Object.entries(value)" in source
    assert 'return value ? "Да" : "Нет"' in source


def test_closed_groups_and_narrow_screens_do_not_expand_page() -> None:
    css = (ROOT / "src/marketcore/presentation/ui_runtime/assets/v2/workspace_v2.css").read_text()
    assert 'details[data-mc-section-group]:not([open]) > :not(summary)' in css
    assert "display: none !important" in css
    assert "@media (max-width: 1100px)" in css
    assert "overflow-x: clip" in css


def test_ui_server_handles_refreshes_concurrently() -> None:
    source = (ROOT / "src/scripts/research/serve_read_only_system_status_ui_v1.py").read_text()
    assert "ThreadingHTTPServer" in source
    assert 'ThreadingHTTPServer(("0.0.0.0", PORT), Handler).serve_forever()' in source


def test_right_control_drawer_prioritizes_problems_and_persists_state() -> None:
    shell = (ROOT / "src/marketcore/presentation/ui_runtime/assets/v2/workspace_shell_bootstrap_v2.js").read_text()
    css = (ROOT / "src/marketcore/presentation/ui_runtime/assets/v2/workspace_v2.css").read_text()
    assert "installControlDrawer" in shell
    assert "marketcore.workspace-v2.drawer-collapsed" in shell
    assert '.sort((left, right) => (right.blocked - left.blocked)' in shell
    assert 'button.dataset.severity = blocked > 0 ? "BLOCKED"' in shell
    assert '#marketcore-control-drawer[data-collapsed="true"]' in css
    assert '.mc-control-drawer-groups button[data-severity="BLOCKED"]' in css
    assert "mc-control-drawer-opportunities" in shell
    assert '[data-mc-status="OOS_PASS"]' in shell
    assert '.mc-control-drawer-groups button[data-severity="SUCCESS"]' in css


def test_runtime_i18n_has_observed_missing_statuses() -> None:
    sql = (ROOT / "sql/analytics/171_ui_runtime_resilience_i18n_v1.sql").read_text()
    assert "status.shadow_heartbeat_older_than_10_minutes" in sql
    assert "status.edge_search_executor_failed:discover_regime" in sql
    assert "ON CONFLICT(resource_key,locale_code) DO UPDATE" in sql
