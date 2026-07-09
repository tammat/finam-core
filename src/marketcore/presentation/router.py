from __future__ import annotations

from marketcore.presentation.workspace_v2.home_page_v2 import (
    render_workspace_v2_home_page_v2,
)
from marketcore.presentation.workspace_v2.portfolio_page_v2 import (
    render_workspace_v2_portfolio_page_v2,
)


def route(path: str) -> tuple[int, bytes]:
    if path in ("/", "/workspace-v2", "/workspace-v2/"):
        return 200, render_workspace_v2_home_page_v2().encode("utf-8")

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
