from __future__ import annotations

from marketcore.presentation.render_tree.http_response_v1 import (
    RenderTreeHttpResponseV1,
    build_render_tree_http_response_v1,
)
from marketcore.presentation.workspace_v2.presenter.home_v2_presenter import (
    HomeV2Presenter,
)
from marketcore.presentation.workspace_v2.presenter.portfolio_v2_presenter import (
    PortfolioV2Presenter,
)
from marketcore.presentation.workspace_v2.renderer.home_v2_renderer import (
    render_home_v2,
)
from marketcore.presentation.workspace_v2.renderer.portfolio_v2_renderer import (
    render_portfolio_v2,
)


def home_render_tree_http_v1() -> RenderTreeHttpResponseV1:
    view_model = HomeV2Presenter().load()
    document = render_home_v2(view_model)

    return build_render_tree_http_response_v1(document)


def portfolio_render_tree_http_v1(
    *,
    theme_code: str = "DEFAULT",
) -> RenderTreeHttpResponseV1:
    view_model = PortfolioV2Presenter().load(limit=200)
    document = render_portfolio_v2(
        view_model,
        theme_code=theme_code,
    )

    return build_render_tree_http_response_v1(document)
