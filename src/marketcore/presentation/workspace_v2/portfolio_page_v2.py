from __future__ import annotations

from marketcore.presentation.render_tree.html_adapter import HtmlAdapter
from marketcore.presentation.workspace_v2.presenter.portfolio_v2_presenter import (
    PortfolioV2Presenter,
)
from marketcore.presentation.workspace_v2.renderer.portfolio_v2_renderer import (
    render_portfolio_v2,
)


def render_workspace_v2_portfolio_page_v2(
    theme_code: str = "DEFAULT",
) -> str:
    vm = PortfolioV2Presenter().load(limit=200)
    document = render_portfolio_v2(vm, theme_code=theme_code)
    return HtmlAdapter.render(document)


if __name__ == "__main__":
    print(render_workspace_v2_portfolio_page_v2())
