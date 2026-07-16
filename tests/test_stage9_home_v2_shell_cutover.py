from pathlib import Path

from marketcore.presentation.router import route


def test_root_uses_v2_shell_without_css_or_domain_markup() -> None:
    status, body = route("/")
    text = body.decode("utf-8")
    assert status == 200
    assert 'data-marketcore-ui-runtime="v2"' in text
    assert "/ui-runtime/v1/" not in text
    assert ".css" not in text
    assert "data-mc-node" not in text
    assert "home.workspace.title" not in text


def test_v2_shell_maps_every_canonical_container() -> None:
    source = Path(
        "src/marketcore/presentation/ui_runtime/assets/v2/workspace_shell_bootstrap_v2.js"
    ).read_text()
    for target in (
        "home", "capital", "edge", "research", "intraday",
        "portfolio", "risk", "program", "settings",
    ):
        assert f'"container.{target}"' in source
    assert "/api/v1/" not in source


def test_legacy_home_render_tree_is_explicitly_retired() -> None:
    status, body = route("/api/v1/render-tree/home")
    assert status == 410
    assert b"LEGACY_PRESENTATION_RETIRED" in body
    assert b"/api/v2/domain-render-tree/home" in body


def test_all_legacy_presentation_entrypoints_are_retired() -> None:
    for path in (
        "/api/v1/render-tree/portfolio",
        "/api/v1/render-tree/portfolio/phone",
        "/api/v2/render-tree/control-center/edge",
        "/assets/marketcore/ui-runtime/v1/runtime.js",
    ):
        status, body = route(path)
        assert status == 410, path
        assert b"LEGACY_PRESENTATION_RETIRED" in body, path


def test_old_workspace_bookmarks_open_the_v2_shell() -> None:
    for path in ("/workspace-v2/portfolio", "/workspace-v2/control-center/edge-oos"):
        status, body = route(path)
        assert status == 200, path
        assert b'data-marketcore-ui-runtime="v2"' in body, path


def test_legacy_state_changing_routes_cannot_execute() -> None:
    from marketcore.presentation.router import route_post

    status, body = route_post("/workspace-v2/control-center/edge-oos/run")
    assert status == 410
    assert b"LEGACY_PRESENTATION_RETIRED" in body


def test_router_has_no_legacy_renderer_or_asset_dependencies() -> None:
    source = Path("src/marketcore/presentation/router.py").read_text()
    for forbidden in (
        "load_ui_runtime_asset_v1",
        "portfolio_render_tree_http_v1",
        "control_center_render_tree_http_v2",
        "render_workspace_v2_portfolio_page_v2",
        "edge_oos_control_center_v1",
    ):
        assert forbidden not in source
