from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_action_controller_keeps_navigation_working_on_plain_http_safari():
    source = (ROOT / "src/marketcore/presentation/ui_runtime/assets/v2/browser_action_controller_v2.js").read_text()
    assert "ACTION_REQUEST_ID_GENERATOR_UNAVAILABLE" not in source
    assert "globalObject.Math.random()" in source
    assert "bytes[6] = (bytes[6] & 0x0f) | 0x40" in source
    assert "bytes[8] = (bytes[8] & 0x3f) | 0x80" in source


def test_workspace_shell_has_routes_for_every_home_tile_target():
    shell = (ROOT / "src/marketcore/presentation/ui_runtime/assets/v2/workspace_shell_bootstrap_v2.js").read_text()
    renderer = (ROOT / "src/marketcore/presentation/workspace_v2/renderer/home_v2_domain_renderer.py").read_text()
    for target in (
        "container.research",
        "container.edge",
        "container.intraday",
        "container.risk",
        "container.program",
        "container.capital",
        "container.portfolio",
    ):
        assert f'"{target}"' in renderer
        assert f'"{target}": "/api/v2/domain-render-tree/' in shell


def test_top_status_tiles_route_to_their_responsible_workspaces():
    renderer = (ROOT / "src/marketcore/presentation/workspace_v2/renderer/home_v2_domain_renderer.py").read_text()
    assert '"home.traffic.data": "container.research"' in renderer
    assert '"home.traffic.edge": "container.edge"' in renderer
    assert '"home.traffic.forward": "container.intraday"' in renderer
    assert '"home.traffic.execution": "container.intraday"' in renderer
    assert '"home.traffic.live": "container.edge"' in renderer
