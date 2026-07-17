from pathlib import Path


def test_research_domain_codes_use_i18n_keys() -> None:
    renderer = Path(
        "src/marketcore/presentation/workspace_v2/renderer/research_v2_domain_renderer.py"
    ).read_text()
    assert 'return f"research.domain.{code}"' in renderer
    assert 'args={"tooltip_key": f"{key}.tooltip"}' in renderer
    assert 'value=item.status,fmt="DOMAIN_CODE"' not in renderer
    assert 'value=item.reason,fmt="DOMAIN_CODE"' not in renderer
    assert 'value=item.recommendation,fmt="DOMAIN_CODE"' not in renderer


def test_workspace_and_research_audit_use_available_width() -> None:
    css = Path(
        "src/marketcore/presentation/ui_runtime/assets/v2/workspace_v2.css"
    ).read_text()
    assert '[data-mc-node="workspace"] { width: 100%; max-width: none;' in css
    assert '[data-mc-node-id="research.audit.table"] { width: 100%; min-width: 0; table-layout: fixed; }' in css
    assert ':nth-child(8) { width: 26%; }' in css


def test_research_domain_i18n_covers_current_system_codes() -> None:
    migration = Path("sql/presentation/075_research_domain_i18n_v1.sql").read_text()
    for key in (
        "research.domain.succeeded",
        "research.domain.failed",
        "research.domain.no_pass",
        "research.domain.edge_search_completed_without_pass",
        "research.domain.keep_gates_and_expand_evidence",
        "research.domain.negative_cost_adjusted_expectancy",
    ):
        assert key in migration


def test_i18n_tooltips_expand_short_labels_in_russian() -> None:
    migration = Path("sql/presentation/075_research_domain_i18n_v1.sql").read_text()
    runtime = Path(
        "src/marketcore/presentation/ui_runtime/assets/v2/domain_render_tree_runtime_v2.js"
    ).read_text()
    driver = Path(
        "src/marketcore/presentation/ui_runtime/assets/v2/browser_platform_driver_v2.js"
    ).read_text()
    assert "research.domain.no_pass.tooltip" in migration
    assert "tooltipValue = translate(" in runtime
    assert 'element.setAttribute("title", String(context.tooltipValue))' in driver
