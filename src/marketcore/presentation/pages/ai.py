from __future__ import annotations

from marketcore.presentation.page import Page


class AiPage(Page):
    def __init__(self) -> None:
        super().__init__(
            route="/ai",
            title="AI",
            icon="✦",
            menu_order=110,
        )

    def render(self) -> str:
        return """
        <section class="card">
            <h2>AI</h2>
            <p>Раздел подключён к MarketCore UI Shell. Функциональное наполнение будет добавлено отдельным этапом.</p>
        </section>
        """
