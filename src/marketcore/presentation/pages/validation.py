from __future__ import annotations

from marketcore.presentation.page import Page


class ValidationPage(Page):
    def __init__(self) -> None:
        super().__init__(
            route="/validation",
            title="Validation",
            icon="✓",
            menu_order=80,
        )

    def render(self) -> str:
        return """
        <section class="card">
            <h2>Validation</h2>
            <p>Раздел подключён к MarketCore UI Shell. Функциональное наполнение будет добавлено отдельным этапом.</p>
        </section>
        """
