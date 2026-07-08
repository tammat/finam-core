from __future__ import annotations

from marketcore.presentation.page import Page
from marketcore.presentation.providers.operator_home_widgets_provider import OperatorHomeWidgetsProvider
from marketcore.presentation.widgets.renderer import render_widgets


class OperatorHomePage(Page):
    def __init__(self) -> None:
        super().__init__(
            route="/",
            title="page.operator_home.title",
            icon="🧠",
            menu_order=1,
        )

    def render(self) -> str:
        widgets = OperatorHomeWidgetsProvider().load()
        return f"""
        <section class="operator-home-v2" data-dashboard-id="operator.home.v2">
            {render_widgets(widgets)}
        </section>
        """
