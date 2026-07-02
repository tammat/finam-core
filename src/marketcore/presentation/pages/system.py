from __future__ import annotations

from marketcore.presentation.page import Page


class SystemPage(Page):
    def __init__(self) -> None:
        super().__init__(
            route="/system",
            title="System",
            icon="⚙",
            menu_order=100,
        )

    def render(self) -> str:
        return """
        <section class="card">
            <h2>System</h2>
            <p>Раздел подключён к MarketCore UI Shell. Функциональное наполнение будет добавлено отдельным этапом.</p>
        </section>
        """
