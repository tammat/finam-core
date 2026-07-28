from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_control_uses_clean_v5_cohort_without_mixing_legacy_scopes() -> None:
    resolver = (ROOT / "src/marketcore/presentation/workspace_v2/resolver/control_compact_v3_resolver.py").read_text()
    renderer = (ROOT / "src/marketcore/presentation/workspace_v2/renderer/control_compact_v3_domain_renderer.py").read_text()
    assert "analytics.closed_trades_fresh_v5_confirmed" in resolver
    assert "FRESH_V5_CONFIRMED_EQUITY" in resolver
    assert "FRESH_V5_CONFIRMED_FUTURES" in resolver
    assert "closed_trades_active_v3" not in resolver
    assert '"V5 всего"' in renderer
    assert '"Исключено"' in renderer
    assert '"Открыто Paper"' in renderer
    assert "def _utc(value):" in renderer
    assert "браузер показывает его в Europe/Moscow" in renderer
    assert '_scope_section("FRESH_V5_CONFIRMED_EQUITY"' in renderer


def test_v4_read_access_is_explicitly_read_only() -> None:
    migration = (ROOT / "sql/analytics/201_control_v4_read_access_v1.sql").read_text()
    assert "GRANT SELECT ON analytics.closed_trades_fresh_v4_regime TO alex, finam" in migration
    assert "GRANT INSERT" not in migration
    assert "GRANT UPDATE" not in migration
