from __future__ import annotations

from marketcore.presentation.ui_runtime.asset_delivery_v1 import (
    load_ui_runtime_asset_v1,
)

from marketcore.presentation.workspace_v2.render_tree_http_v1 import (
    home_render_tree_http_v1,
    portfolio_render_tree_http_v1,
)

from marketcore.presentation.workspace_v2.portfolio_page_v2 import (
    render_workspace_v2_portfolio_page_v2,
)
from marketcore.presentation.workspace_v2.edge_oos_control_center_v1 import (
    render_edge_oos_control_center_v1,
    run_hypothesis_action_v1,
    run_lead_lag_action_v1,
    run_oos_action_v1,
)


def route(path: str, query: dict[str, list[str]] | None = None) -> tuple[int, bytes]:
    query = query or {}
    if path in (
        "/workspace-v2",
        "/workspace-v2/",
    ):
        response = load_ui_runtime_asset_v1(
            "/workspace-v2"
        )
        return response.status_code, response.body

    if path == "/":
        response = load_ui_runtime_asset_v1(
            "/workspace-v2"
        )
        return response.status_code, response.body

    if path.startswith("/assets/marketcore/ui-runtime/v1/"):
        response = load_ui_runtime_asset_v1(path)
        return response.status_code, response.body

    if path in (
        "/api/v1/render-tree/home",
        "/api/v1/render-tree/home/",
    ):
        response = home_render_tree_http_v1()
        return response.status_code, response.body

    if path in (
        "/api/v1/render-tree/portfolio",
        "/api/v1/render-tree/portfolio/",
    ):
        response = portfolio_render_tree_http_v1()
        return response.status_code, response.body

    if path in (
        "/api/v1/render-tree/portfolio/phone",
        "/api/v1/render-tree/portfolio/phone/",
    ):
        response = portfolio_render_tree_http_v1(
            theme_code="PHONE",
        )
        return response.status_code, response.body


    if path in ("/workspace-v2/portfolio", "/workspace-v2/portfolio/"):
        return 200, render_workspace_v2_portfolio_page_v2(
            timezone=(query.get("timezone") or [None])[0],
            currency=(query.get("currency") or [None])[0],
            broker=(query.get("broker") or [None])[0],
        ).encode("utf-8")

    if path in ("/workspace-v2/control-center/edge-oos", "/workspace-v2/control-center/edge-oos/"):
        return 200, render_edge_oos_control_center_v1().encode("utf-8")


    if path in ("/workspace-v2/portfolio/phone",):
        return (
            200,
            render_workspace_v2_portfolio_page_v2(
                theme_code="PHONE",
            ).encode("utf-8"),
        )

    return 404, b"Not found"


def route_post(path: str) -> tuple[int, bytes]:
    if path == "/workspace-v2/control-center/edge-oos/run":
        notice = run_oos_action_v1()
        return 200, render_edge_oos_control_center_v1(notice).encode("utf-8")
    if path == "/workspace-v2/control-center/edge-oos/discover":
        notice = run_hypothesis_action_v1()
        return 200, render_edge_oos_control_center_v1(notice).encode("utf-8")
    if path == "/workspace-v2/control-center/edge-oos/lead-lag":
        notice = run_lead_lag_action_v1()
        return 200, render_edge_oos_control_center_v1(notice).encode("utf-8")
    return 404, b"Not found"
