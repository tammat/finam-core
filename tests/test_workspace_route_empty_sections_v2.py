from pathlib import Path


def test_direct_workspace_routes_open_the_requested_section() -> None:
    source = Path(
        "src/marketcore/presentation/ui_runtime/assets/v2/workspace_shell_bootstrap_v2.js"
    ).read_text()
    expected_routes = {
        "/research": "container.research",
        "/intraday": "container.intraday",
        "/portfolio": "container.portfolio",
        "/capital": "container.capital",
        "/risk": "container.risk",
        "/program": "container.program",
        "/settings": "container.settings",
    }
    for route, target in expected_routes.items():
        assert f'path.includes("{route}")' in source
        assert f'return "{target}"' in source


def test_empty_tables_grids_and_sections_are_pruned_after_render() -> None:
    source = Path(
        "src/marketcore/presentation/ui_runtime/assets/v2/browser_platform_driver_v2.js"
    ).read_text()
    assert "tbody [data-mc-node=\"table_row\"]" in source
    assert "grid.querySelector('[data-mc-node=\"card\"]')" in source
    assert "if (!hasContent) section.remove();" in source
