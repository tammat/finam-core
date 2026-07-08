from __future__ import annotations

from marketcore.presentation.dashboard.renderer import render_dashboard
from marketcore.presentation.page import Page
from marketcore.presentation.providers.operator_home_provider import OperatorHomeProvider


class OperatorHomePage(Page):
    def __init__(self) -> None:
        super().__init__(
            route="/",
            title="page.operator_home.title",
            icon="🧠",
            menu_order=1,
        )

    def render(self) -> str:
        vm = OperatorHomeProvider().load()
        return render_dashboard(vm)
