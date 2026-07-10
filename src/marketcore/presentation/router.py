from __future__ import annotations

from marketcore.presentation.workspace_v2.render_tree_http_v1 import (
    home_render_tree_http_v1,
    portfolio_render_tree_http_v1,
)

from marketcore.presentation.workspace_v2.home_page_v2 import (
    render_workspace_v2_home_page_v2,
)
from marketcore.presentation.workspace_v2.portfolio_page_v2 import (
    render_workspace_v2_portfolio_page_v2,
)


def route(path: str) -> tuple[int, bytes]:
    if path in ("/", "/workspace-v2", "/workspace-v2/"):
        return 200, render_workspace_v2_home_page_v2().encode("utf-8")

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
        return 200, render_workspace_v2_portfolio_page_v2().encode("utf-8")


    if path in ("/workspace-v2/portfolio/phone",):
        return (
            200,
            render_workspace_v2_portfolio_page_v2(
                theme_code="PHONE",
            ).encode("utf-8"),
        )

    return 404, b"Not found"
