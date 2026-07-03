from __future__ import annotations

from marketcore.presentation.page import Page


class RiskPage(Page):
    def __init__(self) -> None:
        super().__init__(
            route="/risk",
            title="Риски",
            icon="⚠",
            menu_order=70,
        )

    def render(self) -> str:
        return """
        <section class="card">
            <h2>Риски</h2>
            <p>Раздел подключён к MarketCore UI Shell. Функциональное наполнение будет добавлено отдельным этапом.</p>
        </section>
        """
