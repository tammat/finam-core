from __future__ import annotations

from marketcore.presentation.page import Page


class ResearchPage(Page):
    def __init__(self) -> None:
        super().__init__(
            route="/research",
            title="Research",
            icon="⌕",
            menu_order=40,
        )

    def render(self) -> str:
        return """
        <section class="card">
            <h2>Research</h2>
            <p>Раздел подключён к MarketCore UI Shell. Функциональное наполнение будет добавлено отдельным этапом.</p>
        </section>
        """
