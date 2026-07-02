from __future__ import annotations

from marketcore.presentation.page import Page


class HomePage(Page):
    def __init__(self) -> None:
        super().__init__(
            route="/",
            title="MarketCore OS",
            icon="⌂",
            menu_order=10,
        )

    def render(self) -> str:
        return """
        <section class="card">
            <h2>MarketCore OS</h2>
            <p>Platform M2 started. UI Shell is active.</p>
        </section>
        """
