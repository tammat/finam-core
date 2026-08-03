from pathlib import Path


def test_operational_ui_uses_only_fresh_v5_scopes():
    source = Path(
        "src/marketcore/presentation/workspace_v2/resolver/control_compact_v3_resolver.py"
    ).read_text()

    active_scopes = source.split("ACTIVE_SCOPES = (", 1)[1].split(")", 1)[0]
    assert "FRESH_V5" in active_scopes
    assert "FRESH_V3" not in active_scopes
    assert "FRESH_V4" not in active_scopes
    assert "WHERE p.portfolio_scope IN %s" in source


def test_morning_audit_is_exposed_on_ui():
    resolver = Path(
        "src/marketcore/presentation/workspace_v2/resolver/control_compact_v3_resolver.py"
    ).read_text()
    renderer = Path(
        "src/marketcore/presentation/workspace_v2/renderer/home_compact_v1_domain_renderer.py"
    ).read_text()

    assert "reachable_shadow_morning_audit_v1" in resolver
    assert "Утренний аудит" in renderer
