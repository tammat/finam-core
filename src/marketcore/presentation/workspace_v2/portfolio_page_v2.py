from __future__ import annotations

from marketcore.presentation.adapters.web.render_document_to_html_v1 import RenderDocumentToHtmlV1
from marketcore.presentation.workspace_v2.presenter.portfolio_v2_presenter import (
    PortfolioV2Presenter,
)
from marketcore.presentation.workspace_v2.renderer.portfolio_v2_renderer import (
    render_portfolio_v2,
)
from marketcore.presentation.services.operator_settings_v1 import OperatorSettingsV1


def render_workspace_v2_portfolio_page_v2(
    theme_code: str = "DEFAULT",
    *,
    timezone: str | None = None,
    currency: str | None = None,
    broker: str | None = None,
) -> str:
    settings = OperatorSettingsV1.load(timezone=timezone, currency=currency, broker=broker)
    vm = PortfolioV2Presenter(settings).load(limit=200)
    document = render_portfolio_v2(vm, theme_code=theme_code, settings=settings)
    content = RenderDocumentToHtmlV1.render(document)
    return f"""<!doctype html>
<html lang="ru">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">
<title>MarketCore — Портфель</title>
<link rel="stylesheet" href="/assets/marketcore/ui-runtime/v1/runtime.css">
</head>
<body data-timezone="{settings.timezone}" data-currency="{settings.currency}" data-broker="{settings.broker}">
<nav class="mc-workspace-nav" aria-label="Основная навигация">
  <a class="mc-workspace-nav__home" href="/">← Главная</a>
  <a href="/workspace-v2/control-center/edge-oos">Control Center</a>
</nav>
<div data-marketcore-ui-runtime="v1">{content}</div>
<script src="/assets/marketcore/ui-runtime/v1/portfolio-workspace.js"></script>
</body>
</html>"""


if __name__ == "__main__":
    print(render_workspace_v2_portfolio_page_v2())
