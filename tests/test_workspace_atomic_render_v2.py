from pathlib import Path


def test_workspace_render_is_committed_atomically() -> None:
    bootstrap = Path(
        "src/marketcore/presentation/ui_runtime/assets/v2/browser_bootstrap_v2.js"
    ).read_text()
    shell = Path(
        "src/marketcore/presentation/ui_runtime/assets/v2/workspace_shell_v2.html"
    ).read_text()

    assert 'const stagingElement = options.documentObject.createElement("div")' in bootstrap
    assert "mountElement: stagingElement" in bootstrap
    assert "options.mountElement.replaceChildren(...stagingElement.childNodes)" in bootstrap
    assert "workspace.css?v=20260719.1" in shell
    assert "browser-bootstrap.js?v=20260719.1" in shell


def test_current_research_timeout_has_russian_translation() -> None:
    migration = Path(
        "sql/presentation/131_research_timeout_i18n_v1.sql"
    ).read_text()
    assert "research.domain.edge_search_step_timeout.discover_regime" in migration
    assert "Тайм-аут режима" in migration
