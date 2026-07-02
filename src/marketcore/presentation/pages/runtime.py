from __future__ import annotations

from marketcore.presentation.page import Page


class RuntimePage(Page):
    def __init__(self) -> None:
        super().__init__(
            route="/runtime",
            title="Runtime",
            icon="▶",
            menu_order=20,
        )

    def render(self) -> str:
        return """
        <section class="card">
            <h2>Runtime</h2>
            <p>Раздел подключён к MarketCore UI Shell. Функциональное наполнение будет добавлено отдельным этапом.</p>
        </section>
        """
